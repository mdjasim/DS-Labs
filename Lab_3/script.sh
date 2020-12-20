#!/bin/bash



#tests to see if the solution is eventuall consistens.
for ((i = 1; i >= 0; i--))
do
curl -d 'entry=node 1 test'${i} -X 'POST' 'http://10.1.0.1:80/board' & 
curl -d 'entry=nod 2 test'${i} -X 'POST' 'http://10.1.0.2:80/board' &
curl -d 'entry=nod 3 test'${i} -X 'POST' 'http://10.1.0.3:80/board' &  


#test to see what happens if two hosts try delete the same entry.
#curl -d 'entry=node 1 test'${i} -X 'POST' 'http://10.1.0.1:80/board' & 
#curl -d 'delete=1' -X 'POST' 'http://10.1.0.2:80/board/3/' &  
#curl -d 'delete=1' -X 'POST' 'http://10.1.0.2:80/board/3/' &  


#Test to see what happens if two hosts try modify the same entry kind of at the same time.
#curl -d 'entry=node 1 test'${i} -X 'POST' 'http://10.1.0.1:80/board' & 
#curl -d 'entry=Modified from node 1' -X 'POST' 'http://10.1.0.1:80/board/2/' &  
#curl -d 'entry=Again modified from node 2' -X 'POST' 'http://10.1.0.2:80/board/2/' & 

done

