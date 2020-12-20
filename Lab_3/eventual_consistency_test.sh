#!/bin/bash

for ((i = 1; i >= 0; i--))
do
curl -d 'entry=node 1 test'${i} -X 'POST' 'http://10.1.0.1:80/board' & 
curl -d 'entry=nod 2 test'${i} -X 'POST' 'http://10.1.0.2:80/board' &
curl -d 'entry=nod 3 test'${i} -X 'POST' 'http://10.1.0.3:80/board' &  
done