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
import operator
from threading import Thread
from datetime import datetime

from bottle import Bottle, run, request, template
import requests

ACTION_ADD = 'add'
ACTION_MODIFY = 'modify'
ACTION_REMOVE = 'remove'

class Entry(object):
    def __init__(self, action, sequence_number, node_id, time, entry = None, status= None):

        self.action = action
        self.sequence_number = sequence_number
        self.entry = entry
        self.node_id = node_id
        self.time = time
        self.status = status
 
        self.mod_time = datetime(1900, 1, 1)

        return

# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    board = {}                      #Board object which is mainly used to display board content
    entries_in_board = {}           #Entry details with time stamps 
    modify_remove_requests = []     #Action logs for the entry which are yet to come; For example remove request came before add request 

    sequence_number = 1           
    node_id = None
    vessel_list = {}


    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def add_new_element_to_board(entry_sequence, element, from_node, time_stamp, is_propagated_call=False):
        global board, sequence_number, entries_in_board
        success = False
        try:

            # Checking if there is any entry with same seqeunce  
            if int(entry_sequence) in board.keys():

                old_entry = entries_in_board[int(entry_sequence)]
                date_new = datetime.strptime(str(time_stamp), '%Y-%m-%d %H:%M:%S.%f')
                date_old = datetime.strptime(str(old_entry.time), '%Y-%m-%d %H:%M:%S.%f')

                # Checking if the incoming entry has older time stamp
                if date_new < date_old or (date_old == date_new and from_node < old_entry.node_id):

                    add_new_element_to_board(int(entry_sequence)+1, old_entry.entry, old_entry.node_id, old_entry.time, True)
                    modify_element_in_store(int(entry_sequence), element, date_new)

                    #Storing new element in form of Entry object with details data like timestamp
                    entries_in_board[int(entry_sequence)] = Entry(ACTION_ADD, entry_sequence, from_node, time_stamp, element)

                    return

                else:
                    add_new_element_to_board(int(entry_sequence)+1, element, from_node, time_stamp, True)
                    return

            #If no entry with same entry sequence simply add entry to board 
            board[int(entry_sequence)] = element
            
            #Storing new element in form of Entry object with details data like timestamp
            entries_in_board[int(entry_sequence)] = Entry(ACTION_ADD, entry_sequence, from_node, time_stamp, element)
            success = True
            sequence_number += 1
        except Exception as e:
            print e
        return success


    def modify_element_in_store(entry_sequence, element, is_propagated_call=False):
        global board
        success = False

        try:
            board[int(entry_sequence)] = element
            success = True
            print "Modified spot: " + str(entry_sequence) + " too: "+ str(element)

        except Exception as e:
            print e
        return success

    def delete_element_from_store(entry_sequence, is_propagated_call = False):
        global board, entries_in_board
        success = False

        try:
        	del board[int(entry_sequence)]
        	success = True

        except Exception as e:
            print e

        entries_in_board[int(entry_sequence)].status = "removed"
        return success

 

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        try:
            url = 'http://{}{}'.format(vessel_ip, path)
            if 'POST' in req:
                res = requests.post(url, data=payload, timeout=(3, 1))
            elif 'GET' in req:
                res = requests.post(url, timeout=(3, 1))
            else:
                print 'Non implemented feature!'
                res = 0
            # result is in res.text or res.json()
            print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload=None, req='POST'):
        global vessel_list, node_id
        for vessel_id, vessel_ip in vessel_list.items():
            #if int(vessel_id) == 4 and int(node_id) == 1:
                #time.sleep(6)
            if int(vessel_id) != node_id: # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    #print "\n\nCould not contact vessel {}\n\n".format(vessel_id)
                    thread = Thread(target=retry_req, args=(vessel_ip, path, payload, req))
                    thread.daemon = True
                    thread.start()

    def retry_req(vessel_ip, path, payload, req='POST'):
        max_time = 30
        sleep = 1
        success = False
        while not success:
            print("\nCould not contact vessel {}. Try again in {} seconds ...".format(vessel_ip, sleep))
            time.sleep(sleep)
            success = contact_vessel(vessel_ip, path, payload, req)
            sleep = min(sleep * 2, max_time)


    #Method that creates separete threads when propagating to all other vessels.
    def propagate_to_all_vessels(path, payload=None, req='POST'):
        thread = Thread(target=propagate_to_vessels, args=(path, payload, req))
        thread.daemon = True
        thread.start()

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()), members_name_string='Jasim & Saif')
                                 
    @app.get('/board')
    def get_board():
        global board, node_id
        print board
        return template('server/boardcontents_template.tpl',board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()))
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        global board, node_id, sequence_number
        try:

            new_entry = request.forms.get('entry')
            time_stamp = datetime.now()

            propagate_to_all_vessels("/propagate/{}/{}/{}".format(ACTION_ADD,sequence_number, node_id), {"entry": new_entry, "time": time_stamp })
            handle_action_recieved(ACTION_ADD, sequence_number, node_id, new_entry, time_stamp)
            
        except Exception as e:
            print e
        return False


    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        global board, entries_in_board
        try:

            print "Recieved action!"
            action = request.forms.get("delete")
            entry = request.forms.get('entry')
            time_stamp = entries_in_board.get(element_id).time
            node = entries_in_board.get(element_id).node_id

            if action == "1":

                propagate_to_all_vessels("/propagate/{}/{}/{}".format(ACTION_REMOVE,element_id, node), {"time": time_stamp})
                handle_action_recieved(ACTION_REMOVE, element_id, node, entry, time_stamp)

            else:
                mod_time = datetime.now()
                propagate_to_all_vessels("/propagate/{}/{}/{}".format(ACTION_MODIFY,element_id, node), {"entry": entry, "time": time_stamp, "time_stamp" : mod_time})
                handle_action_recieved(ACTION_MODIFY, element_id, node, entry, time_stamp, mod_time)
                
        except Exception as e:
            print e
        return False

    @app.post('/propagate/<action>/<element_id>/<node_id>')
    def propagation_received(action, element_id, node_id):
        try: 

            entry_msg = request.forms.get("entry")
            time = request.forms.get("time")
            mod_time = False

            if action == ACTION_MODIFY:
                mod_time = request.forms.get("time_stamp")

            handle_action_recieved(action, element_id, node_id, entry_msg, time, mod_time)

            return "Success"
        except Exception as e:
            print e
        return "Internal Error"

    def handle_action_recieved(action, element_id, node_id, entry_msg, time_stamp, mod_time = False):
        global  modify_remove_requests, board, entries_in_board
        try:

            if action == ACTION_ADD:
                #If there is already a modify or remove request for the add request, we need to handle that first
                if modify_remove_requests:
                    for entry in modify_remove_requests:
                        if str(entry.time) == str(time_stamp) and int(entry.node_id) == int(node_id):
                            if entry.action == ACTION_REMOVE:
                                modify_remove_requests.remove(entry)
                                print modify_remove_requests
                                entries_in_board[int(entry.sequence_number)] = Entry(ACTION_ADD, entry.sequence_number, entry.node_id, time_stamp, entry_msg, "removed")
                                return

                            elif entry.action == ACTION_MODIFY:
                                add_new_element_to_board(element_id, entry.entry, node_id, time_stamp)
                                return

                #Otherwise just add new entry to the board
                add_new_element_to_board( int(element_id), entry_msg, node_id, time_stamp, True)

            elif (action == ACTION_REMOVE or action == ACTION_MODIFY):
                for entries in entries_in_board.values():
                    if int(entries.node_id) == int(node_id) and str(entries.time) == str(time_stamp): 
                        if action == ACTION_REMOVE and not entries.status == "removed":
                            delete_element_from_store(entries.sequence_number, True)
                            return

                        elif action == ACTION_MODIFY and not entries.status == "removed":
                            mod_time = datetime.strptime(str(mod_time), '%Y-%m-%d %H:%M:%S.%f')                           
                            if entries.mod_time < mod_time:
                                modify_element_in_store(entries.sequence_number, entry_msg, True)
                                entries_in_board[int(entries.sequence_number)].mod_time = mod_time
                                entries_in_board[int(entries.sequence_number)].entry = entry_msg
                                return

                        return

                #Loggin the remove or modify request
                modify_remove_requests.append(Entry(action, element_id, node_id, time_stamp, entry_msg))
            
            return "Success"
        except Exception as e:
            print e
        return "Internal Error"


    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    def main():
        global vessel_list, node_id, app

        port = 80
        parser = argparse.ArgumentParser(description='Group 11 implementation of the distributed blackboard')
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
