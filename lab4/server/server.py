# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 4 (Byzantine Agreement)
# server/server.py
# Input: Total number of servers; --servers = 4
# Students: Jasim & Saif
# ------------------------------------------------------------------------------------------------------
from bottle import Bottle, run, request, template, HTTPResponse
import requests

import traceback
import sys
import time
import json
import argparse
import byzantine_behavior
from threading import Thread
# ------------------------------------------------------------------------------------------------------
try:
    # ------------------------------------------------------------------------------------------------------
    # APPLICATION INITIALIZATION AND CONSTANTS
    # ------------------------------------------------------------------------------------------------------
    app = Bottle()
    ATTACK = "ATTACK"
    RETREAT = "RETREAT"
    BYZANTINE = "BYZANTINE"
    
    # ------------------------------------------------------------------------------------------------------
    # LOCAL STATE - VOTES AND VECTORS 
    # ------------------------------------------------------------------------------------------------------
    number_of_nodes = None # Total number of nodes. will be override by value given with start arugument
    votes = {}  # Own view about the votes; It is populated during step 1
    result_vectors = {}  # Vector collections other node's votes including Byzatine node
    concensus = None
    final_votes = None
    byzantine = False
    

    # ------------------------------------------------------------------------------------------------------
    # VOTES AND AGREEMENT LOGIC
    # ------------------------------------------------------------------------------------------------------    
    def prepare_final_result_vector():
        result_vector = []
        attack = None
        retreat = None
        print votes
        # Calculating votes for each column in the result vectors;
        for i in range(1, number_of_nodes + 1):
            # The count will be reset for new column
            attack = 0
            retreat = 0
            for j, vec in result_vectors.iteritems():
                # First we are checking what we have got from the selected node; This is the votes we got in the first round
                # For example while we are in process node 2 we will give priority to vote we got from node 2
                # So we will take value from 'votes' dictionary instead of result vector
                if int(j) == i:
                    if votes.get(str(i)) == ATTACK:
                        attack += 1
                    if votes.get(str(i)) == RETREAT:
                        retreat += 1
                else:  
                # Here will take from result vector when we are processing for other node.
                # For example when we are processing node 3 (i.e. i = 3) and for value j = 2 we need to get votes from result vector 
                    if vec.get(str(i)) == ATTACK:
                        attack += 1
                    if vec.get(str(i)) == RETREAT:
                        retreat += 1
            
            # Generating result vector for current node.
            if attack >= retreat:
                result_vector.append(ATTACK)
            else:
                result_vector.append(RETREAT)
        return result_vector

    # Here we determine whats the concensus and the final votes vector
    # It returns two value. Final agreement as 'concensus' and votes as 'final_result_vectors'
    def make_concensus():
        final_result_vectors = prepare_final_result_vector()
        concensus = None
        attack = 0
        retreat = 0
        for v in final_result_vectors:
            if v == ATTACK:
                attack += 1
            else:
                retreat += 1

        # Decide final winner.
        if attack >= retreat:
            concensus = ATTACK
        else:
            concensus = RETREAT
        return concensus, final_result_vectors

    # Converting bolean values to a vote dictionary got from Byzantine behavior fro round two
    def convert_to_dictionary(arr):
        i = 0
        byzantine_dict = {}
        for vessel_id, vessel_ip in vessel_list.items():
            byzantine_dict[vessel_id] = convert_to_attack_or_retreat(arr[i])
            i += 1
        return byzantine_dict

    # Check if all the votes came is then perfor the byzantine step two
    def perform_byzantine_step_two():
        global node_id
        if byzantine and len(votes) == number_of_nodes:
            res = byzantine_behavior.compute_byzantine_vote_round2(number_of_nodes - 1, number_of_nodes, True)
            propogate_byzantine_step_two(res, node_id)
        if len(votes) == number_of_nodes and not byzantine:
            propogate_result(node_id)
                
    
    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        try:
            if 'POST' in req:
                res = requests.post(
                    'http://{}{}'.format(vessel_ip, path), json=payload)
            elif 'GET' in req:
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print 'Non implemented feature!'
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload=None, req='POST'):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id: # Ignoring myself
                t = Thread(target=contact_vessel, args=(
                        vessel_ip, path, payload, req))
                t.daemon = True
                t.start()

    def propogate_client_vote(decision, node_id):
        path = "/propagate/{}/{}".format(decision, node_id)
        propagate_to_vessels(path)

    def propogate_result(node_id):
        payload = {'status': votes}
        path = "/propagate/result/{}".format(node_id)
        propagate_to_vessels(path, payload)

    def convert_to_attack_or_retreat(val):
        if val:
            return ATTACK
        else:
            return RETREAT

    def propogate_byzantine_step_one(arr, node_id):
        i = 0
        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # Ignoring myself
                path = "/propagate/{}/{}".format(convert_to_attack_or_retreat(arr[i]), node_id)  
                t = Thread(target=contact_vessel, args=(
                        vessel_ip, path))
                t.daemon = True
                t.start()
                i += 1
    
    def propogate_byzantine_step_two(arr_of_arr, node_id):
        i = 0
        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:
                byzantine_dict = convert_to_dictionary(arr_of_arr[i]) 
                payload = {'status': byzantine_dict}
                
                path = "/propagate/result/{}".format(node_id)
                t = Thread(target=contact_vessel, args=(
                        vessel_ip, path, payload))
                t.daemon = True
                t.start()
                i += 1
                 

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # Routes methods and implementation of voting interface
    # ------------------------------------------------------------------------------------------------------

    @app.route('/')
    def index():
        global node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), members_name_string='Jasim & Saif')

    @app.get('/vote/result')
    def get_result():
        global node_id, concensus, final_votes
        # Have received all other nodes vectors
        if len(result_vectors) == number_of_nodes - 1:
            if concensus == None and final_votes == None:
               concensus, final_votes = make_concensus()
            return template('server/result_template.tpl', result=concensus, result_vector=final_votes)
        pass

    @app.post('/vote/attack')
    def client_attack_received():
        global node_id
        propogate_client_vote(ATTACK, node_id)
        votes[node_id] = ATTACK
        perform_byzantine_step_two()
        return format_response(200)

    @app.post('/vote/retreat')
    def client_retreat_received():
        global node_id
        propogate_client_vote(RETREAT, node_id)
        votes[node_id] = RETREAT
        perform_byzantine_step_two()
        return format_response(200)

    @app.post('/vote/byzantine')
    def client_byzantine_received():
        global node_id, byzantine
        res = byzantine_behavior.compute_byzantine_vote_round1(number_of_nodes - 1, number_of_nodes, True)
        byzantine = True
        votes[node_id] = BYZANTINE
        propogate_byzantine_step_one(res, node_id)
        perform_byzantine_step_two()
        return format_response(200)

    #Propagation of Byzantine step 2
    @app.post('/propagate/result/<node_id>')
    def propagation_result_received(node_id):
        json_dict = request.json
        status_dict_for_node = json_dict.get('status')
        result_vectors[node_id] = status_dict_for_node
        return format_response(200)


    # Propagation of Byzantine step 1
    @app.post('/propagate/<vote>/<external_node_id>')
    def propagation_received(vote, external_node_id):
        global node_id
        votes[external_node_id] = vote
        perform_byzantine_step_two()
        return format_response(200)

 
    def format_response(status_code, message=''):
        '''
        Simple function for formatting response code.
        '''
        if status_code == 200:
            return HTTPResponse(status=200)
        return HTTPResponse(status=status_code, body={'message': message})
    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    # Main function from where execution of the code start

    def main():
        global vessel_list, node_id, app, number_of_nodes

        port = 80
        parser = argparse.ArgumentParser(
            description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid',
                            default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1,
                            type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        number_of_nodes = args.nbv # Setting number of nodes from the arguments
        vessel_list = dict()
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv+1):
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        try:
            run(app, host=vessel_list[str(node_id)], port=port)
        except Exception as e:
            print e
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
    traceback.print_exc()
    while True:
        time.sleep(60.)
