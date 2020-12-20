#!/bin/bash

for ((i = 1; i >= 0; i--))
do 
curl -d 'entry=node 1 test'${i} -X 'POST' 'http://10.1.0.1:80/board' & 
curl -d 'delete=1' -X 'POST' 'http://10.1.0.2:80/board/3/' &  
curl -d 'delete=1' -X 'POST' 'http://10.1.0.2:80/board/3/' &  
done

