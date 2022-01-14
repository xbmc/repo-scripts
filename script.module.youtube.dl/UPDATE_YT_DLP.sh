#! /usr/bin/sh
#
# The only thing to build is to update yt-dlp, as needed.
# The export/yt-dlp directory is a submodule of the yt-dlp
# project. It should be updated to the latest
# yt-dlp release branch and then the appropriate 
# code copied to the lib directory.
# 
cd external/yt-dlp
git branch link_yt_dlp

# Get latest release. Verify with yt-dlp
# project that the build is good and that
# this is still correct branch, etc.

git checkout release 
cd ..  # To external directory

# Must add this version of submodule to branch again

git add  yt-dlp 

# Replace old version of code

git rm -r resources/lib/yt_dlp
cp -rp external/yt-dlp/yt_dlp resources/lib/yt_dlp

# Update version

cat  <<eof >/tmp/youtube-dl.tmp
/(^[^_])|^$/d;/__version__/s/(^[^']*')|('$)//g
eof

echo 
echo Update the addon.xml to have a prefix of the yt-dlp version + .x
echo addon version bump. ex: 2021.12.27.0

echo 
echo current yt-dlp version:
sed -rf /tmp/youtube-dl.tmp external/yt-dlp/yt_dlp/version.py

echo 
echo checkin all files, as appropriate
