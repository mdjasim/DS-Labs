# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: Node_ID total_number_of_ID
# Student: Jasim & Saif
# ------------------------------------------------------------------------------------------------------
import traceback
import sys
import time
import json
import argparse
from threading import Thread
from bottle import Bottle, run, request, template
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    #board stores all message on the system 
    board = {0 : "Welcome to Distributed Systems Course"} 
    
    #global entry counter
    message_id = 0;
    
    #Action constant
    ACTION_CONSTANT_ADD = 'ADD'
    ACTION_CONSTANT_MODIFY = 'MODIFY'
    ACTION_CONSTANT_DELETE = 'DELETE'

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # Add, Modify and Delete
    # ------------------------------------------------------------------------------------------------------
    
    #This functions will add an new element
    def add_new_element_to_store(entry_sequence, element, is_propagated_call=False):
        global board, message_id
        success = False
        try:
           if entry_sequence not in board: #Entry only added if it is not in the board already
                board[entry_sequence] = element
                
                #Updating global counter
                message_id = entry_sequence
                success = True
        except Exception as e:
            print e
        return success

    def modify_element_in_store(entry_sequence, modified_element, is_propagated_call = False):
        global board
        success = False
        try:
            #Modify entry by given entry sequence on the board
            board[entry_sequence] = modified_element
            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(entry_sequence, is_propagated_call = False):
        global board
        success = False
        try:
            #delete entry from the board
            del board[entry_sequence]
            success = True
        except Exception as e:
            print e
        return success

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id),
                board_dict=sorted({"0":board,}.iteritems()), members_name_string='Jasim and Saif')

    @app.get('/board')
    def get_board():
        global board, node_id
        print board
        return template('server/boardcontents_template.tpl',board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()))
    
    #------------------------------------------------------------------------------------------------------
    
    # Post entry directly to a board
    @app.post('/board')
    def client_add_received():
        try:
            # Get the entry from the HTTP body
            new_entry = request.forms.get('entry')
            
            '''Assign element id to the new entry
            It is done by increasing global message_id by 1'''
            element_id = message_id + 1 
            
            #Adding the entry to own board
            add_new_element_to_store(element_id, new_entry)
            
            # Propagate action to all other nodes
            thread = Thread(target=propagate_to_vessels,
                            args=('/propagate/{}/'.format(ACTION_CONSTANT_ADD) + str(element_id), {'entry': new_entry}, 'POST'))
            thread.daemon = True
            thread.start()
        except Exception as e:
            print e
        return False

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        # Get the entry from the HTTP body
        entry = request.forms.get('entry')
        
        # Get the action from the HTTP body
        #0 = modify, 1 = delete
        delete_option = request.forms.get('delete')
        
        #call either delete or modify based on delete_option value
        if delete_option == '0':
            modify_element_in_store(element_id, entry, False)
            propagate_action = ACTION_CONSTANT_MODIFY
        elif delete_option == '1':
            delete_element_from_store(element_id, False)
            propagate_action = ACTION_CONSTANT_DELETE
        else:
            print 'Unknown action!'
        
        # Propagate action to all other nodes
        thread = Thread(target=propagate_to_vessels,
                            args=('/propagate/{}/'.format(propagate_action) + str(element_id), {'entry': entry}, 'POST'))
        thread.daemon = True
        thread.start()
    
    #With this function we handle requests from other nodes like add modify or delete
    @app.post('/propagate/<action>/<element_id:int>')
    def propagation_received(action, element_id):
	    #get entry from http body
        entry = request.forms.get('entry')
        
        # Handle actions add modify or delete
        if action == ACTION_CONSTANT_ADD:
            add_new_element_to_store(element_id, entry, True)
        elif action == ACTION_CONSTANT_MODIFY:
            modify_element_in_store(element_id, entry, True)
        elif action == ACTION_CONSTANT_DELETE:
            delete_element_from_store(element_id, True)
        else:
            print 'Non implemented action!'
        
       
    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        try:
            if 'POST' in req:
                res = requests.post('http://{}{}'.format(vessel_ip, path), data=payload)
            elif 'GET' in req:
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print 'Non implemented feature!'
            # result is in res.text or res.json()
            print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload = None, req = 'POST'):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id: # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

        
    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    def main():
        global vessel_list, node_id, app

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
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
