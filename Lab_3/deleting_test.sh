#!/bin/bash

curl -d 'delete=1' -X 'POST' 'http://10.1.0.1:80/board/1/' &  
curl -d 'delete=1' -X 'POST' 'http://10.1.0.2:80/board/1/' &  
