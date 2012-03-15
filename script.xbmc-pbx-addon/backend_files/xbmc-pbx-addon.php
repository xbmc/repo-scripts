<?php
#  XBMC PBX Addon
#      Back-end (Asterisk PBX) side
#      This script is used to access Call Detail Records (CDR) and VoiceMail (VM)
#
#
#  Copyright (C) 2012 hmronline@gmail.com 
#  http://xbmc-pbx-addon.googlecode.com
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

// Script constants
$__addon__              = "XBMC PBX Addon";
$__addon_id__           = "script.xbmc-pbx-addon";
$__author__             = "hmronline";
$__url__                = "http://code.google.com/p/xbmc-pbx-addon/";
$__version__            = "1.0.10";


// ************************************************************************************************************
// YOU MAY WANT TO CUSTOMIZE THIS:
$cdr_filename           = "/var/log/asterisk/cdr-csv/Master.csv";
$vm_path                = '/var/spool/asterisk/voicemail/';
// ************************************************************************************************************
$ami_path               = "/etc/asterisk/";


//#############################################################################################################
if (isset($_GET['recindex']) && isset($_GET['mailbox']) && isset($_GET['vmcontext']) && isset($_GET['format'])) {
    $vm_path .= $_GET['vmcontext'] . "/" . $_GET['mailbox'];
    if (isset($_GET['delete'])) {
        //
        // VoiceMail Deletion
        //
        header("content-type: text/plain");
        echo $__addon__ ." ". $__version__;
        echo "\nVoiceMail Deletion\n";
        $vm_path .= "/INBOX/";
        if (is_dir($vm_path)) {
            if ($dirhandle = @opendir($vm_path)) {
                while (false !== ($filename = readdir($dirhandle))) {
                    if (strpos($filename,"msg". $_GET['recindex'] .".") === 0) {
                        $file_to_delete = $vm_path . $filename;
                        echo "\nDeleting file: ". $file_to_delete;
                        unlink($file_to_delete);
                    }
                }
            }
            closedir($dirhandle);
            echo "\nDone.\n";
        }
    }
    elseif (isset($_GET['store'])) {
        //
        // VoiceMail Storing
        //
        header("content-type: text/plain");
        echo $__addon__ ." ". $__version__;
        echo "\nVoiceMail Storing\n";
        if (is_dir($vm_path ."/INBOX/")) {
            if ($dirhandle = @opendir($vm_path ."/INBOX/")) {
                while (false !== ($filename = readdir($dirhandle))) {
                    if (strpos($filename,"msg". $_GET['recindex'] .".") === 0) {
                        $file_to_store = $vm_path ."/INBOX/". $filename;
                        echo "\nStoring file: ". $file_to_store;
                        if (copy($file_to_delete,$vm_path ."/Old/")) {
                            unlink($file_to_delete);
                        }
                    }
                }
            }
            closedir($dirhandle);
            echo "\nDone.\n";
        }
    }
    else {
        //
        // VoiceMail Download
        //
        // Based on http://www.freepbx.org/trac/browser/freepbx/branches/2.7/amp_conf/htdocs/recordings/misc/audio.php
        //
        $file_to_download = $vm_path ."/INBOX/"."msg". $_GET['recindex'] .".". $_GET['format'];
        // See if the file exists
        if (!is_file($file_to_download)) { die("\n404 File not found!"); }
        // Gather relevent info about file
        $size = filesize($file_to_download);
        $name = basename($file_to_download);
        $extension = strtolower(substr(strrchr($name,"."),1));
        // This will set the Content-Type to the appropriate setting for the file
        $ctype = '';
        switch ($extension) {
            case "mp3": $ctype = "audio/mpeg"; break;
            case "wav": $ctype = "audio/x-wav"; break;
            case "WAV": $ctype = "audio/x-wav"; break; //wav49
            case "gsm": $ctype = "audio/x-gsm"; break;
            // not downloadable
            default: die("\n404 File not found!"); break ;
        }
        // need to check if file is mislabeled or a liar.
        $fp = fopen($file_to_download, "rb");
        if ($size && $ctype && $fp) {
            header("Pragma: public");
            header("Expires: 0");
            header("Cache-Control: must-revalidate, post-check=0, pre-check=0");
            header("Cache-Control: public");
            header("Content-Description: VoiceMail Download");
            header("Content-Type: " . $ctype);
            header("Content-Disposition: attachment; filename=" . $name);
            header("Content-Transfer-Encoding: binary");
            header("Content-length: " . $size);
            fpassthru($fp);
        }
    }
}
elseif (isset($_GET["cdr"]) || isset($_GET["vm"])) {
    header("content-type: text/xml");
    $xmldoc = new DOMDocument();
    if (!is_object($xmldoc)) { die("<pbx><error>Not able to create a XML object. Is php-xml installed?</error></pbx>"); }
    $xmldoc->preserveWhiteSpace = false;
    $xmldoc->formatOutput = true;
    $xmlroot = $xmldoc->createElement("pbx");
    $xmldoc->appendChild($xmlroot);
    $node = $xmldoc->createElement("version");
    $node->appendChild($xmldoc->createTextNode($__version__));
    $xmlroot->appendChild($node);
    if (isset($_GET["cdr"])) {
        //
        // Call Detail Records (CDR)
        //
        $cdr_fields = array('accountcode','src','dst','dcontext',
            'clid','channel','dstchannel','lastapp','lastdata',
            'start','answer','end','duration','billsec',
            'disposition','amaflags','uniqueid','userfield');
        // Read CSV file and store into an Array
        $cdr = array();
        if (is_readable($cdr_filename)) {
            if (($handle = fopen($cdr_filename, "r")) !== FALSE) {
                while (($cdr_data = fgetcsv($handle, 4096, ",")) !== FALSE) {
                    $cdr[] = $cdr_data;
                }
                fclose($handle);
            }
        }
        else {
            $node = $xmldoc->createElement("cdr_error");
            $element = $xmldoc->createElement("msg");
            $element->appendChild($xmldoc->createTextNode("Unable to read file: " . $cdr_filename));
            $node->appendChild($element);
            $xmlroot->appendChild($node);
        }
        // Filter, resize and reverse
        $cdr = array_slice($cdr,-50);
        $cdr = array_reverse($cdr);
        // Convert CDR Array into XML
        for ($i=0; $i < count($cdr); $i++) {
            $node = $xmldoc->createElement("cdr");
            for ($c=0; $c < count($cdr[$i]); $c++) {
                $element = $xmldoc->createElement($cdr_fields[$c]);
                $element->appendChild($xmldoc->createTextNode(utf8_encode($cdr[$i][$c])));
                $node->appendChild($element);
            }
            $xmlroot->appendChild($node);
        }
        unset($cdr);
    }
    if (isset($_GET["vm"]) && isset($_GET['mailbox']) && isset($_GET['vmcontext'])) {
        //
        // VoiceMail List
        //
        $vm_path .= $_GET['vmcontext'] . "/" . $_GET['mailbox'] . "/INBOX/";
        if (is_readable($vm_path)) {
            if ($handle = opendir($vm_path)) {
                $vm = array();
                while (false !== ($file = readdir($handle))) {
                    if ($file != "." && $file != ".." && strpos($file,".txt")) {
                        $vm[str_replace(".txt","",str_replace("msg","",$file))] = parse_ini_file($vm_path . $file);
                    }
                }
                closedir($handle);
            }
        }
        else {
            $node = $xmldoc->createElement("vm_error");
            $element = $xmldoc->createElement("msg");
            $element->appendChild($xmldoc->createTextNode("Unable to read directory: " . $vm_path));
            $node->appendChild($element);
            $xmlroot->appendChild($node);
        }
        // Order, filter, resize and reverse
        array_sort_by_column($vm, 'origtime');
        $vm = array_slice($vm,-50);
        $vm = array_reverse($vm);
        // Convert VM Array into XML
        if (count($vm) > 0) {
            foreach ($vm as $i => $c) {
                $node = $xmldoc->createElement("vm");
                $element = $xmldoc->createElement("recindex");
                $element->appendChild($xmldoc->createTextNode($i));
                $node->appendChild($element);
                foreach ($c as $key => $val) {
                    $element = $xmldoc->createElement($key);
                    if ($key == 'origtime') {
                        $val = date("Y-m-d H:i:s",$val);
                    }
                    $element->appendChild($xmldoc->createTextNode(utf8_encode($val)));
                    if ($key != 'origdate') {
                        $node->appendChild($element);
                    }
                }
                $xmlroot->appendChild($node);
            }
        }
        unset($vm);
    }
    // Print CDR + VM XML
    echo $xmldoc->saveXML();
    echo "<!-- ". $__addon__ ." ". $__version__ ." -->";
    unset($xmldoc);
}
else {
    //
    // Instructions
    //
    header ("content-type: text/html");
    $html_content  = "<html>\n";
    $html_content .= "<head><title>". $__addon__ ." ". $__version__ ."</title></head>\n";
    $html_content .= "<body>\n";
    $html_content .= "<h1>". $__addon__ ." ". $__version__ ."</h1>\n";
    $html_content .= "<table border='1' cellpadding='1' cellspacing='1'>\n";
    $html_content .= "<tr><th colspan=2>Back-end (PBX Server) Side Setup</th></tr>\n";
    $html_content .= "<tr><td>Able to access VoiceMail (VM) directory <br/>(". $vm_path .")</td><td>";
    if (!is_dir($vm_path)) {
        $html_content .= "ERROR";
        $found_err = true;
    }
    else {
        $html_content .= "OK";
    }
    $html_content .= "</td></tr>\n";
    $html_content .= "<tr><td>Able to write into VoiceMail (VM) directory <br/>(". $vm_path .")</td><td>";
    if (!is_writable(dirname($vm_path))) {
        $html_content .= "ERROR";
        $found_err = true;
    }
    else {
        $html_content .= "OK";
    }
    $html_content .= "</td></tr>\n";
    $html_content .= "<tr><td>Able to read Call Detail Record (CDR) file <br/>(". $cdr_filename .")</td><td>";
    if (!is_readable($cdr_filename)) {
        $html_content .= "ERROR";
        $found_err = true;
    }
    else {
        $html_content .= "OK";
    }
    $html_content .= "</td></tr>\n";
    $html_content .= "<tr><td>Able to create a XML object <br/>(Is php-xml installed?)</td><td>";
    $xmldoc = new DOMDocument();
    if (!is_object($xmldoc)) {
        $html_content .= "ERROR";
        $found_err = true;
    }
    else {
        $html_content .= "OK";
    }
    unset($xmldoc);
    $html_content .= "</td></tr>\n";
    if (is_readable($ami_path)) {
        if ($handle = opendir($ami_path)) {
            $ami = array();
            while (false !== ($file = readdir($handle))) {
                if ($file != "." && $file != ".." && strpos($file,"manager") === 0 && strrpos($file,".conf",-6) === false) {
                    $ami[] = parse_ini_file($ami_path . $file,true);
                }
            }
            closedir($handle);
            foreach ($ami as $arr_tmp) {
                if (array_key_exists("xbmc",$arr_tmp)) {
                    $ami_found = true;
                }
            }
        }
    }
    $html_content .= "<tr><td>Asterisk Manager Interface (AMI) is configured for this addon <br/>(i.e. /etc/asterisk/manager_custom.conf)</td><td>";
    if ($ami_found != true) {
        $html_content .= "ERROR";
        $found_err = true;
    }
    else {
        $html_content .= "OK";
    }
    $html_content .= "</td></tr>\n";
    $html_content .= "</table>\n";
    if ($found_err) {
        $html_content .= "<p>Errors found. Please check this file, update paths accordingly and fix any errors.</p>\n";
    }
    else {
        $html_content .= "<p>Seems everything is ok on the Back-end (PBX Server) side. 
                            <br/>Please continue the setup on the Front-end (XBMC) side.</p>\n";
    }
    $html_content .= "</body></html>";
    echo $html_content;
}
function array_sort_by_column(&$arr, $col, $dir = SORT_ASC) {
    $sort_col = array();
    foreach ($arr as $key => $row) {
        $sort_col[$key] = $row[$col];
    }
    array_multisort($sort_col, $dir, $arr);
}
?>
