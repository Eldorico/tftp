#!/bin/sh
fileName="test7777k"
serverPort="69"
host="localhost"
serverDirectory="serverFiles"

echo downloading $fileName from hepia.infolibre.ch... This will take 5 minutes
python src/client.py -get hepia.infolibre.ch 69 $fileName
echo downloading finished.

echo md5 sum after downloading from hepia.infolibre.ch:
md5sum $fileName

echo starting server
mkdir -p $serverDirectory
python src/server.py -p $serverPort -d $serverDirectory & 
serverPID=$!
echo server started. PID : $serverPID

echo uploading file to local server...
python src/client.py -put $host $serverPort $fileName

echo removing first downloaded file
rm $fileName

echo downloading file from local server 
python src/client.py -get $host $serverPort $fileName

echo md5 sum after downloading from hepia.infolibre.ch:
md5sum $fileName

echo stoping server
kill $serverPID

echo removing files
rm -r $serverDirectory $fileName
