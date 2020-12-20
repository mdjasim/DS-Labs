#!/bin/bash

for ((i = 1; i <= 2; i++))
do
curl -d 'entry=Node 1 test '${i} -X 'POST' 'http://10.1.0.1:80/board' & 
curl -d 'entry=Node 2 test '${i} -X 'POST' 'http://10.1.0.2:80/board' &
curl -d 'entry=Node 3 test '${i} -X 'POST' 'http://10.1.0.3:80/board' &  
done
