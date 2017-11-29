# script.module.addon.signals
Provides signal/slot mechanism for inter-addon communication in Kodi

```python
# In target addon
import AddonSignals
​
def callback(data):
	# Do something with data
	
AddonSignals.registerSlot('sender.addon.id', 'signal_name', callback)
​
​
#In source addon
import AddonSignals
​
AddonSignals.sendSignal('signal_name', {'some': 'data'})
```
