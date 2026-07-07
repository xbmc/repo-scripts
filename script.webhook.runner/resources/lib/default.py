"""
Webhook Runner - Simple webhook management with direct Keymap Editor integration
"""
import sys
import os
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
WEBHOOKS_FILE = os.path.join(ADDON_DATA, 'webhooks.json')
EVENTS_FILE = os.path.join(ADDON_DATA, 'events.json')

# Events the background service can fire webhooks on. Order = menu order.
EVENT_NAMES = [
    ('playback_start',  'Playback started'),
    ('playback_stop',   'Playback stopped'),
    ('playback_pause',  'Playback paused'),
    ('playback_resume', 'Playback resumed'),
    ('screensaver_on',  'Screensaver activated'),
    ('screensaver_off', 'Screensaver deactivated'),
    ('kodi_start',      'Kodi started'),
    ('kodi_stop',       'Kodi stopping'),
]

# Keymap Editor's file
KEYMAPS_DIR = xbmcvfs.translatePath('special://userdata/keymaps/')
GEN_XML_FILE = os.path.join(KEYMAPS_DIR, 'gen.xml')

# The button-mapping feature writes/deletes the shared Kodi keymap file
# (special://userdata/keymaps/gen.xml), which lives outside this addon's
# profile folder. Kodi repo policy requires explicit user opt-in before an
# addon touches files elsewhere, so we ask once and remember the answer.
# (Event triggers do NOT need this - they only use events.json in profile.)
KEYMAP_CONSENT_FILE = os.path.join(ADDON_DATA, 'keymap_consent')


def L(string_id):
    """Shorthand for a localized string from resources/language/*/strings.po."""
    return ADDON.getLocalizedString(string_id)


def has_keymap_consent():
    return os.path.exists(KEYMAP_CONSENT_FILE)


def ensure_keymap_consent():
    """Ask the user (once) to allow writing the shared Kodi keymap file.

    Returns True if allowed. The consent is remembered in the addon profile
    so the prompt only appears the first time a button mapping is created.
    """
    if has_keymap_consent():
        return True
    allowed = xbmcgui.Dialog().yesno(
        L(32004),  # "Keymap Permission"
        L(32005),  # explanation of what will be written and where
        yeslabel=L(32006), nolabel=L(32007))
    if not allowed:
        return False
    ensure_data_dir()
    try:
        with open(KEYMAP_CONSENT_FILE, 'w', encoding='utf-8') as f:
            f.write('1')
    except Exception:
        pass
    # Clean up any leftover keymap files from older versions now that we're
    # permitted to touch the keymaps directory.
    for old_file in ['webhook_runner.xml', 'zzz_webhook_runner.xml']:
        old_path = os.path.join(KEYMAPS_DIR, old_file)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
    return True

# Action ID to key name (for auto-detect)
ACTION_TO_KEY = {
    1: 'up', 2: 'down', 3: 'left', 4: 'right',
    7: 'select', 9: 'back', 10: 'back', 92: 'back',
    11: 'info', 117: 'contextmenu',
    58: 'zero', 59: 'one', 60: 'two', 61: 'three', 62: 'four',
    63: 'five', 64: 'six', 65: 'seven', 66: 'eight', 67: 'nine',
    68: 'play', 69: 'pause', 70: 'stop',
    77: 'fastforward', 78: 'rewind', 87: 'playpause',
    88: 'volumeplus', 89: 'volumeminus', 91: 'mute',
    122: 'red', 123: 'green', 124: 'yellow', 125: 'blue',
    180: 'channelup', 181: 'channeldown',
    186: 'pageup', 187: 'pagedown',
    175: 'guide', 190: 'menu', 216: 'homepage',
}


def ensure_data_dir():
    if not os.path.exists(ADDON_DATA):
        os.makedirs(ADDON_DATA)


def show_notification(title, message, ms=2000):
    if ADDON.getSettingBool("show_notifications"):
        xbmc.executebuiltin(f'Notification({title},{message},{ms})')


# ============================================================================
# WEBHOOK STORAGE
# ============================================================================

def load_webhooks():
    ensure_data_dir()
    if os.path.exists(WEBHOOKS_FILE):
        try:
            with open(WEBHOOKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_webhooks(webhooks):
    ensure_data_dir()
    try:
        with open(WEBHOOKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(webhooks, f, indent=2)
        return True
    except:
        return False


def get_webhook(webhook_id):
    return load_webhooks().get(str(webhook_id))


def get_all_webhooks():
    webhooks = load_webhooks()
    result = []
    for wh_id, wh_data in webhooks.items():
        result.append({
            'id': wh_id,
            'name': wh_data.get('name', f'Webhook {wh_id}'),
            'url': wh_data.get('url', ''),
            'enabled': wh_data.get('enabled', True),
            'button': wh_data.get('button'),
            'button_type': wh_data.get('button_type', 'remote')
        })
    result.sort(key=lambda x: int(x['id']) if x['id'].isdigit() else x['id'])
    return result


def get_next_id():
    webhooks = load_webhooks()
    if not webhooks:
        return "1"
    max_id = 0
    for wh_id in webhooks.keys():
        try:
            if int(wh_id) > max_id:
                max_id = int(wh_id)
        except:
            pass
    return str(max_id + 1)


def add_webhook(name, url):
    webhooks = load_webhooks()
    new_id = get_next_id()
    webhooks[new_id] = {'name': name, 'url': url, 'enabled': True, 'button': None, 'button_type': 'remote'}
    save_webhooks(webhooks)
    return new_id


def update_webhook(webhook_id, **kwargs):
    webhooks = load_webhooks()
    wh_id = str(webhook_id)
    if wh_id not in webhooks:
        return False
    for key, value in kwargs.items():
        webhooks[wh_id][key] = value
    return save_webhooks(webhooks)


def delete_webhook(webhook_id):
    webhooks = load_webhooks()
    wh_id = str(webhook_id)
    if wh_id in webhooks:
        button = webhooks[wh_id].get('button')
        button_type = webhooks[wh_id].get('button_type', 'remote')
        del webhooks[wh_id]
        save_webhooks(webhooks)
        if button:
            remove_from_keymap(button, button_type)
        return True
    return False


# ============================================================================
# KEYMAP (gen.xml)
# ============================================================================

def ensure_keymaps_dir():
    if not os.path.exists(KEYMAPS_DIR):
        os.makedirs(KEYMAPS_DIR)


def load_gen_xml():
    ensure_keymaps_dir()
    if os.path.exists(GEN_XML_FILE):
        try:
            tree = ET.parse(GEN_XML_FILE)
            return tree.getroot()
        except:
            pass
    return ET.Element('keymap')


def save_gen_xml(root):
    ensure_keymaps_dir()
    # Write as single line XML with proper formatting
    xml_string = ET.tostring(root, encoding='unicode', method='xml')
    # Remove all newlines first
    xml_string = ''.join(xml_string.split())
    # Fix spacing issues step by step
    # 1. Fix missing space after key
    xml_string = xml_string.replace('<keyid=', '<key id=')
    # 2. Ensure proper spacing for key elements
    xml_string = xml_string.replace('<keyid', '<key id')
    # 3. Ensure space for <key id=
    xml_string = re.sub(r'<key(?!>)([^>]*)>', r'<key\1>', xml_string)
    xml_string = re.sub(r'<key([^i])', r'<key \1', xml_string)
    # 4. Ensure space before mod attribute
    xml_string = xml_string.replace('"mod="', '" mod="')
    # 5. Remove ALL spaces from specific tags - no spaces anywhere
    xml_string = xml_string.replace('<keymap ', '<keymap')
    xml_string = xml_string.replace('<keymap>', '<keymap>')  # keep as is
    xml_string = xml_string.replace('<keyboard ', '<keyboard')
    xml_string = xml_string.replace('<global ', '<global')
    xml_string = xml_string.replace('<key ', '<key')  # remove all spaces after <key first
    xml_string = xml_string.replace('<keyid=', '<key id=')  # then add back only for id
    # 6. Clean up any double spaces
    xml_string = xml_string.replace('  ', ' ')
    with open(GEN_XML_FILE, 'w', encoding='utf-8') as f:
        f.write(xml_string)
    xbmc.executebuiltin('Action(reloadkeymaps)')


def indent_xml(elem, level=0):
    # Don't add indentation - create single line XML
    pass


def get_or_create(parent, tag):
    elem = parent.find(tag)
    if elem is None:
        elem = ET.SubElement(parent, tag)
    return elem


def add_to_keymap(button, button_type, webhook_id, longpress=False):
    # Writing gen.xml is outside our profile - requires explicit user opt-in.
    if not ensure_keymap_consent():
        return None
    root = load_gen_xml()
    action = f'RunScript({ADDON_ID},{webhook_id})'
    
    # Use keyboard section for raw button codes with id attribute
    if button.isdigit() and int(button) > 1000:
        # Ensure the structure exists: keymap -> global -> keyboard
        global_elem = get_or_create(root, 'global')
        keyboard_elem = get_or_create(global_elem, 'keyboard')
        
        # Check if key with this id AND same longpress mode already exists
        for key_elem in keyboard_elem.findall('key'):
            if key_elem.get('id') == button:
                existing_longpress = key_elem.get('mod') == 'longpress'
                if existing_longpress == longpress:
                    # Same button with same longpress mode already exists
                    if key_elem.text and ADDON_ID in key_elem.text:
                        xbmc.log(f"[Webhook Runner] Warning: Button {button} ({'longpress' if longpress else 'press'}) already mapped to webhook runner", xbmc.LOGWARNING)
                    return key_elem.text  # Return existing mapping
        
        # Create new key element with id attribute
        key_elem = ET.SubElement(keyboard_elem, 'key')
        key_elem.set('id', button)
        if longpress:
            key_elem.set('mod', 'longpress')
        key_elem.text = action
        
    else:
        # Use regular mapping for standard button names
        global_elem = get_or_create(root, 'global')
        device_elem = get_or_create(global_elem, button_type)
        
        existing = device_elem.find(button)
        if existing is not None:
            # Check if it's already mapped to our webhook runner
            if existing.text and ADDON_ID in existing.text:
                xbmc.log(f"[Webhook Runner] Warning: Button {button} already mapped to webhook runner", xbmc.LOGWARNING)
            return existing.text  # Return existing mapping
        
        btn = ET.SubElement(device_elem, button)
        btn.text = action
    
    save_gen_xml(root)
    xbmc.log(f"[Webhook Runner] Mapped: {button} ({'longpress' if longpress else 'press'}) -> webhook {webhook_id}", xbmc.LOGINFO)
    return None


def remove_from_keymap(button, button_type):
    if not os.path.exists(GEN_XML_FILE):
        return
    
    root = load_gen_xml()
    
    # Remove from keyboard section if it's a raw button code
    if button.isdigit() and int(button) > 1000:
        keyboard_elem = root.find('keyboard')
        if keyboard_elem is not None:
            for key_elem in keyboard_elem.findall('key'):
                if key_elem.get('id') == button and key_elem.text and ADDON_ID in key_elem.text:
                    keyboard_elem.remove(key_elem)
                    break
    else:
        # Remove from regular sections
        global_elem = root.find('global')
        if global_elem is None:
            return
        
        # Remove from both button_type and universalremote sections
        for section in [button_type, 'universalremote']:
            device_elem = global_elem.find(section)
            if device_elem is None:
                continue
            
            btn = device_elem.find(button)
            if btn is not None and btn.text and ADDON_ID in btn.text:
                device_elem.remove(btn)
    
    save_gen_xml(root)
    xbmc.log(f"[Webhook Runner] Removed mapping: {button}", xbmc.LOGINFO)


def get_keymap_mappings():
    """Get all our webhook mappings from gen.xml."""
    mappings = {}
    
    if not os.path.exists(GEN_XML_FILE):
        return mappings
    
    try:
        tree = ET.parse(GEN_XML_FILE)
        root = tree.getroot()
    except:
        return mappings
    
    # Check keyboard section for raw button codes
    keyboard_elem = root.find('keyboard')
    if keyboard_elem is not None:
        for key_elem in keyboard_elem.findall('key'):
            if key_elem.text and ADDON_ID in key_elem.text:
                button_id = key_elem.get('id')
                if button_id:
                    try:
                        wh_id = key_elem.text.split(',')[1].rstrip(')')
                        longpress = key_elem.get('mod') == 'longpress'
                        # Create unique key for webhook mapping including longpress status
                        map_key = f"{wh_id}_{button_id}_{'longpress' if longpress else 'press'}"
                        mappings[wh_id] = {
                            'button': button_id, 
                            'button_type': 'keyboard',
                            'longpress': longpress
                        }
                    except:
                        pass
    
    # Check global section for regular mappings
    global_elem = root.find('global')
    if global_elem is not None:
        for device_type in ['remote', 'keyboard', 'universalremote']:
            device_elem = global_elem.find(device_type)
            if device_elem is None:
                continue
            for btn in device_elem:
                if btn.text and ADDON_ID in btn.text:
                    try:
                        wh_id = btn.text.split(',')[1].rstrip(')')
                        if wh_id not in mappings:
                            mappings[wh_id] = {'button': btn.tag, 'button_type': device_type, 'longpress': False}
                    except:
                        pass
    
    return mappings


# ============================================================================
# WEBHOOK EXECUTION
# ============================================================================

def send_webhook(url, name="Webhook"):
    try:
        xbmc.log(f"[Webhook Runner] Sending: {name}", xbmc.LOGINFO)
        data = urllib.parse.urlencode({}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10):
            show_notification("Webhook Sent", name)
            return True
    except Exception as e:
        xbmc.log(f"[Webhook Runner] Error: {e}", xbmc.LOGERROR)
        show_notification("Error", str(e)[:30], 4000)
        return False


def run_webhook(webhook_id):
    webhook = get_webhook(webhook_id)
    if not webhook:
        show_notification("Error", f"Webhook {webhook_id} not found")
        return
    if not webhook.get('enabled', True):
        show_notification("Error", "Webhook disabled")
        return
    if not webhook.get('url'):
        show_notification("Error", "No URL")
        return
    send_webhook(webhook['url'], webhook.get('name', f'Webhook {webhook_id}'))


# ============================================================================
# EVENT TRIGGERS
# ============================================================================

def load_event_map():
    ensure_data_dir()
    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except:
            pass
    return {}


def save_event_map(mapping):
    ensure_data_dir()
    try:
        with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2)
        return True
    except:
        return False


def show_event_triggers_menu():
    dialog = xbmcgui.Dialog()
    while True:
        mapping = load_event_map()
        webhooks = {wh['id']: wh for wh in get_all_webhooks()}

        items = []
        for event_key, label in EVENT_NAMES:
            wh_id = mapping.get(event_key)
            wh_name = webhooks.get(wh_id, {}).get('name') if wh_id else None
            if wh_name:
                items.append(f"{label} → [COLOR cyan]{wh_name}[/COLOR]")
            else:
                items.append(f"{label} → [COLOR grey](none)[/COLOR]")
        items.append('Back')

        choice = dialog.select('Event Triggers', items)
        if choice < 0 or choice == len(items) - 1:
            return

        event_key, event_label = EVENT_NAMES[choice]
        wh_list = get_all_webhooks()
        if not wh_list:
            dialog.ok('Event Triggers', 'Add a webhook first.')
            continue

        options = ['(none)'] + [wh['name'] for wh in wh_list]
        pick = dialog.select(f'Webhook for "{event_label}"', options)
        if pick < 0:
            continue
        if pick == 0:
            mapping.pop(event_key, None)
        else:
            mapping[event_key] = wh_list[pick - 1]['id']
        save_event_map(mapping)


# ============================================================================
# KEY CAPTURE
# ============================================================================

class KeyCaptureWindow(xbmcgui.WindowDialog):
    def __init__(self):
        super().__init__()
        self.key = None
        self.key_type = 'remote'
        self.action_id = None
        self.cancelled = False
    
    def onAction(self, action):
        self.action_id = action.getId()
        self.button_code = action.getButtonCode()  # Get raw button code
        
        if self.action_id in [92, 10, 9]:
            self.cancelled = True
            self.close()
            return
        
        # Always use raw button code if available (overrides any standard action mapping)
        if self.button_code and self.button_code > 1000:
            self.key = str(self.button_code)  # Use raw code as key name
        elif self.action_id in ACTION_TO_KEY:
            self.key = ACTION_TO_KEY[self.action_id]
        else:
            self.key = None  # Unknown - user will type it
        
        self.close()


def capture_button():
    """Capture button and show action ID, let user type name."""
    dialog = xbmcgui.Dialog()
    dialog.notification('Capture', 'Press a button... (Back=cancel)', xbmcgui.NOTIFICATION_INFO, 5000)
    xbmc.sleep(500)
    
    win = KeyCaptureWindow()
    win.doModal()
    
    if win.cancelled:
        del win
        return None, None, False
    
    action_id = win.action_id
    detected_key = win.key
    del win
    
    # Show what was detected and let user confirm or type
    if detected_key:
        # Check if it's a raw button code
        is_raw_code = detected_key.isdigit() and len(detected_key) >= 5
        
        if is_raw_code:
            # For raw codes, automatically use them without asking
            longpress = dialog.yesno('Long Press', 'Should this be triggered on long press?')
            return detected_key, 'keyboard', longpress
        else:
            # For standard keys, show confirmation
            result = dialog.yesno('Button Detected',
                f'Detected: [B]{detected_key}[/B]\n'
                f'Action ID: {action_id}\n\n'
                f'Use this name?',
                yeslabel='Yes', nolabel='Type Different Name')
            
            if result:
                # Ask for device type
                type_choice = dialog.select('Button Type', ['Remote', 'Keyboard'])
                if type_choice < 0:
                    return None, None, False
                longpress = dialog.yesno('Long Press', 'Should this be triggered on long press?')
                return detected_key, 'remote' if type_choice == 0 else 'keyboard', longpress
    
    # User needs to type the name
    key_name = dialog.input(f'Enter button name\n\nAction ID was: {action_id}')
    if not key_name:
        return None, None, False
    
    key_name = key_name.lower().strip()
    
    # Ask for device type
    type_choice = dialog.select('Button Type', ['Remote', 'Keyboard'])
    if type_choice < 0:
        return None, None, False
    
    longpress = dialog.yesno('Long Press', 'Should this be triggered on long press?')
    return key_name, 'remote' if type_choice == 0 else 'keyboard', longpress


def select_button():
    """Let user capture or type a button name."""
    dialog = xbmcgui.Dialog()
    
    options = [
        'Press button to detect',
        'Type button name',
        'Cancel'
    ]
    
    choice = dialog.select('Select Button', options)
    
    if choice == 0:
        return capture_button()
    
    elif choice == 1:
        key = dialog.input('Enter button name (e.g. red, volumeplus, f1)')
        if not key:
            return None, None
        key = key.lower().strip()
        
        type_choice = dialog.select('Button Type', ['Remote', 'Keyboard'])
        if type_choice < 0:
            return None, None
            
        # Ask if this should be a long press
        longpress = dialog.yesno('Long Press', 'Should this be triggered on long press?')
        
        return key, 'remote' if type_choice == 0 else 'keyboard', longpress
    
    return None, None, False


# ============================================================================
# UI
# ============================================================================

def show_main_menu():
    dialog = xbmcgui.Dialog()
    
    while True:
        webhooks = get_all_webhooks()
        keymap = get_keymap_mappings()
        
        # Update with keymap data
        for wh in webhooks:
            if wh['id'] in keymap:
                wh['button'] = keymap[wh['id']]['button']
                wh['button_type'] = keymap[wh['id']]['button_type']
        
        items = []
        for wh in webhooks:
            status = "[COLOR green]●[/COLOR]" if wh['enabled'] else "[COLOR red]○[/COLOR]"
            if wh.get('button'):
                items.append(f"{status} {wh['name']} → [COLOR cyan]{wh['button']}[/COLOR]")
            else:
                items.append(f"{status} {wh['name']}")
        
        items.append('─' * 30)
        items.append('[COLOR lime]+ Add Webhook[/COLOR]')
        items.append('[COLOR yellow]Run Webhook[/COLOR]')
        items.append('[COLOR orange]Event Triggers[/COLOR]')
        items.append('Exit')

        choice = dialog.select('Webhook Runner', items)

        if choice < 0 or 'Exit' in items[choice]:
            return

        if items[choice].startswith('─'):
            continue
        elif 'Add Webhook' in items[choice]:
            add_webhook_dialog()
        elif 'Run Webhook' in items[choice]:
            run_webhook_dialog()
        elif 'Event Triggers' in items[choice]:
            show_event_triggers_menu()
        elif choice < len(webhooks):
            edit_webhook_dialog(webhooks[choice]['id'])


def add_webhook_dialog():
    dialog = xbmcgui.Dialog()
    
    name = dialog.input('Webhook Name')
    if not name:
        return

    prefix = ADDON.getSetting('default_url_prefix') or 'http://'
    url = dialog.input('Webhook URL', defaultt=prefix)
    if not url or url == prefix:
        return
    
    new_id = add_webhook(name, url)
    
    if dialog.yesno('Created', f'Webhook "{name}" created.\n\nMap a button to it now?'):
        result = select_button()
        if result:
            if len(result) == 2:
                button, button_type = result
                longpress = False
            else:
                button, button_type, longpress = result
                
            if button:
                # Check if button is already mapped to any webhook runner action
                existing_mapping = add_to_keymap(button, button_type, new_id, longpress)
                if existing_mapping:
                    if dialog.yesno('Button Already Mapped', 
                                  f'Button {button} is already mapped.\n\n'
                                  f'Existing: {existing_mapping}\n\n'
                                  f'Replace with webhook {new_id}?'):
                        # Remove existing mapping by finding the webhook ID
                        try:
                            existing_wh_id = existing_mapping.split(',')[1].rstrip(')')
                            remove_from_keymap(button, button_type)
                            # Now add the new mapping
                            add_to_keymap(button, button_type, new_id, longpress)
                        except:
                            pass
                    else:
                        return
                
                update_webhook(new_id, button=button, button_type=button_type)
                dialog.notification('Mapped', f'{name} → {button}', xbmcgui.NOTIFICATION_INFO, 2000)


def edit_webhook_dialog(webhook_id):
    dialog = xbmcgui.Dialog()
    
    while True:
        wh = get_webhook(webhook_id)
        if not wh:
            return
        
        keymap = get_keymap_mappings()
        mapping = keymap.get(str(webhook_id))
        
        name = wh.get('name', '')
        url = wh.get('url', '')
        enabled = wh.get('enabled', True)
        button = mapping['button'] if mapping else None
        button_type = mapping['button_type'] if mapping else 'remote'
        
        url_short = url if len(url) <= 35 else url[:35] + '...'
        
        items = [
            f"Name: {name}",
            f"URL: {url_short}",
            f"Enabled: {'Yes' if enabled else 'No'}",
            f"Button: {button or '(none)'}",
            '─' * 30,
            '[COLOR lime]Test[/COLOR]',
            '[COLOR yellow]Map Button[/COLOR]',
        ]
        
        if button:
            items.append('[COLOR orange]Remove Button[/COLOR]')
        
        items.append('[COLOR red]Delete Webhook[/COLOR]')
        items.append('Back')
        
        choice = dialog.select(f'Edit: {name}', items)
        
        if choice < 0 or 'Back' in items[choice]:
            return
        
        selected = items[choice]
        
        if selected.startswith('─'):
            continue
        
        elif selected.startswith('Name:'):
            new_name = dialog.input('Name', defaultt=name)
            if new_name:
                update_webhook(webhook_id, name=new_name)
        
        elif selected.startswith('URL:'):
            new_url = dialog.input('URL', defaultt=url)
            if new_url:
                update_webhook(webhook_id, url=new_url)
        
        elif selected.startswith('Enabled:'):
            update_webhook(webhook_id, enabled=not enabled)
        
        elif selected.startswith('Button:') or 'Map Button' in selected:
            result = select_button()
            if result:
                if len(result) == 2:
                    new_button, new_type = result
                    longpress = False
                else:
                    new_button, new_type, longpress = result
                    
                if new_button:
                    # Check if button is already mapped to any webhook runner action
                    existing_mapping = add_to_keymap(new_button, new_type, webhook_id, longpress)
                    if existing_mapping:
                        if dialog.yesno('Button Already Mapped', 
                                      f'Button {new_button} is already mapped.\n\n'
                                      f'Existing: {existing_mapping}\n\n'
                                      f'Replace with webhook {webhook_id}?'):
                            # Remove existing mapping by finding the webhook ID
                            try:
                                existing_wh_id = existing_mapping.split(',')[1].rstrip(')')
                                remove_from_keymap(new_button, new_type)
                                # Now add the new mapping
                                add_to_keymap(new_button, new_type, webhook_id, longpress)
                            except:
                                pass
                        else:
                            continue
                    
                    # Remove old button mapping for this webhook
                    if button:
                        remove_from_keymap(button, button_type)
                    
                    update_webhook(webhook_id, button=new_button, button_type=new_type)
                    dialog.notification('Mapped', f'{name} → {new_button}', xbmcgui.NOTIFICATION_INFO, 2000)
        
        elif 'Remove Button' in selected:
            if button:
                remove_from_keymap(button, button_type)
                update_webhook(webhook_id, button=None)
                dialog.notification('Removed', 'Button removed', xbmcgui.NOTIFICATION_INFO, 2000)
        
        elif 'Test' in selected:
            run_webhook(webhook_id)
        
        elif 'Delete' in selected:
            if dialog.yesno('Delete', f'Delete "{name}"?'):
                if button:
                    remove_from_keymap(button, button_type)
                delete_webhook(webhook_id)
                return


def run_webhook_dialog():
    dialog = xbmcgui.Dialog()
    webhooks = [wh for wh in get_all_webhooks() if wh['enabled']]
    
    if not webhooks:
        dialog.ok('Run', 'No enabled webhooks.')
        return
    
    items = [wh['name'] for wh in webhooks]
    choice = dialog.select('Run Webhook', items)
    
    if choice >= 0:
        run_webhook(webhooks[choice]['id'])


# ============================================================================
# MAIN
# ============================================================================

def main():
    xbmc.log(f"[Webhook Runner] Started: {sys.argv}", xbmc.LOGINFO)
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        webhook_id = arg.split('=')[1] if '=' in arg else arg
        if webhook_id:
            run_webhook(webhook_id)
            return
    
    show_main_menu()


if __name__ == "__main__":
    main()
