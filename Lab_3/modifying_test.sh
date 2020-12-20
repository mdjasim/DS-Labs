#!/bin/bash

for ((i = 1; i >= 0; i--))
do
curl -d 'entry=node 1 test'${i} -X 'POST' 'http://10.1.0.1:80/board' & 
curl -d 'entry=Modified from node 1' -X 'POST' 'http://10.1.0.1:80/board/2/' &  
curl -d 'entry=Again modified from node 2' -X 'POST' 'http://10.1.0.2:80/board/2/' & 
done