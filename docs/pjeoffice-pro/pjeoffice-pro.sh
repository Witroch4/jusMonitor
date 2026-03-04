#!/bin/bash

debugMode=false

currentDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
currentDIR=$currentDIR | sed -e 's/ /\\ /g'
cd "$currentDIR"
chmod 755 ffmpeg.exe
chmod 755 ./jre/bin/java
a3auto=true
if [ "$debugMode" = false ]; then
	rm -rf ~/.pjeoffice-pro/*.log*
else
    a3auto=false
    rm -rf ~/.pjeoffice-pro
fi

nohup ./jre/bin/java \
-XX:+UseG1GC \
-XX:MinHeapFreeRatio=3 \
-XX:MaxHeapFreeRatio=3 \
-Xms20m \
-Xmx2048m \
-Dpjeoffice_home="$currentDIR" \
-Dffmpeg_home="$currentDIR" \
-Dpjeoffice_looksandfeels="Metal" \
-Dcutplayer4j_looksandfeels="Nimbus" \
-Dsigner4j_a3auto="$a3auto" \
-jar \
pjeoffice-pro.jar >/dev/null 2>&1 &

# Aguarda 1 segundo antes de finalizar a seção atual
sleep 1

# Fecha a tela preta do script
exit
