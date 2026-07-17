service.subtitles.ktuvit
==================

Ktuvit.me subtitle service for Kodi

In order to get the encoded password:

1. Open [ktuvit.me](https://www.ktuvit.me) in the browser
2. Open [developer tools](https://developers.google.com/web/tools/chrome-devtools/open)  (in Windows <kbd>ctrl</kbd> + <kbd>shift</kbd> + <kbd>c</kbd>
)
3. Enter this code in the **console**: 
```javascript
x = { value: 'MY-PASSWORD' };
loginHandler.EncryptPassword({}, x, 'MY@EMAIL.COM');
copy(x.value); // this will copy your encrypted password to your clipboard
console.log(`Now paste it in the addon's settings at the Encrypted password field`)
``` 
![Gujn9Y8vTF](https://user-images.githubusercontent.com/9304194/94992868-897f0100-0595-11eb-8694-0272ae2f19b9.gif)

