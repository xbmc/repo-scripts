### Example usage

```
T9Search(call=self.search,
         start_value="",
         history=self.__class__.__name__ + ".search")
```

call: method to call for live search (should take one param, the search string)
start_value: set search string to some specific initial value
history: settings key to use for saving / loading search history
