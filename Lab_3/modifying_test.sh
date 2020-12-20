#!/bin/bash

curl -d 'entry=Modified from node 1' -X 'POST' 'http://10.1.0.1:80/board/1/' &  
curl -d 'entry=Modified again from node 2' -X 'POST' 'http://10.1.0.2:80/board/1/' & 
