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
from bottle import Bottle, run, request, template, HTTPResponse
import requests
import random

# ------------------------------------------------------------------------------------------------------
# Action Conatants
# ------------------------------------------------------------------------------------------------------
ACTION_CONSTANT_ADD = "add"
ACTION_CONSTANT_MODIFY = "modify"
ACTION_CONSTANT_DELETE = "delete"

# ------------------------------------------------------------------------------------------------------
# BOARD Class
# Add, Modify and Delete and get all entries
# ------------------------------------------------------------------------------------------------------
class Board:
    def __init__(self):
        self.seq_num = 0
        self.entries = {}

    def add(self, entry):
        entry_id = self.seq_num
        self.entries[entry_id] = entry
        self.seq_num += 1
        return entry_id

    def delete(self, id):
        try:
            del self.entries[id]
            return True
        except Exception as e:
            print(e)
        return False

    def modify(self, id, entry):
        try:
            self.entries[id] = entry
            return True
        except Exception as e:
            print(e)
        return False

    def getEntries(self):
        return self.entries

    def get_seq_num(self):
        return self.seq_num

# ------------------------------------------------------------------------------------------------------
# Bollte server configuration
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()
    leader_id = 1
    leader_rand = 0
    board = Board()
    rand_value = random.randint(1, 10000)

    
    def start_leader_election(node_id):
        # Election orgnizer functions; Initiates the election with him own id
        payload = {'max_value': rand_value,
                   'max_node_id': node_id, 'org_sender_id': node_id}
        current_node_id = node_id
        send_election_call_to_next_vessel(current_node_id, payload)

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    def contact_vessel(vessel_id, vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        try:
            if 'POST' in req:
                res = requests.post(
                    'http://{}{}'.format(vessel_ip, path), json=payload)
            elif 'GET' in req:
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print "REQ:"
                print req
                print 'Non implemented feature!'
            # result is in res.text or res.json()
            print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        if not success:
            print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

    def propagate_to_next_vessel_in_thread(next_node_id, next_node_ip, path, payload=None, req='POST'):
        t = Thread(target=contact_vessel, args=(
            next_node_id, next_node_ip, path, payload, req))
        t.daemon = True
        t.start()

    def propagate_to_leader_in_thread(path, payload=None, req='POST'):
        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) == leader_id:
                t = Thread(target=contact_vessel, args=(
                    vessel_id, vessel_ip, path, payload, req))
                t.daemon = True
                t.start()
                break

    def propagate_to_vessels_in_thread(path, payload=None, req='POST'):
        global vessel_list, node_id

        # Loop over vessels
        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                # Start a thread for each propagation
                t = Thread(target=contact_vessel, args=(
                    vessel_id, vessel_ip, path, payload, req))
                t.daemon = True
                t.start()

    def get_path(action, id):
        if (id == None):
            return None

        base_string = '/propagate/{}/{}'
        if (action == ACTION_CONSTANT_ADD):
            return base_string.format(ACTION_CONSTANT_ADD, id)

        if (action == ACTION_CONSTANT_MODIFY):
            return base_string.format(ACTION_CONSTANT_MODIFY, id)

        if (action == ACTION_CONSTANT_DELETE):
            return base_string.format(ACTION_CONSTANT_DELETE, id)
        return None

    def propagate_to_vessels(action, id, payload=None):
        # Validate input
        if (id == None):
            return False

        # Check action
        path = get_path(action, id)

        # Propagate to all vessels in a thread for each request.
        propagate_to_vessels_in_thread(path, payload)
        return True

    def propagate_to_leader(action, id, payload=None):
        # Validate input
        if (id == None):
            return False

        # Check action
        path = get_path(action, id)

        # Propagate to all vessels in a thread for each request.
        propagate_to_leader_in_thread(path, payload)
        return True

    def send_election_call_to_next_vessel(sender_id, payload=None):
        global vessel_list, node_id
        path = '/pick/leader/{}'.format(node_id)

        try:
            # will send the propagation to same next node everytime
            next_node_id = int(node_id) + 1
            next_node_ip = vessel_list.get(str(next_node_id))

            if (next_node_ip == None):
                next_node_ip = vessel_list.get('1')
                next_node_id = 1

            propagate_to_next_vessel_in_thread(
                next_node_id, next_node_ip, path, payload)
            return True

        except Exception as e:
            print(e)
            return False

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id
        entries = board.getEntries()
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(entries.iteritems()), members_name_string='Jasim and Saif', leader_id=leader_id, leader_rand=leader_rand)

    @app.get('/board')
    def get_board():
        global board, node_id
        entries = board.getEntries()
        return template('server/boardcontents_template.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(entries.iteritems()))
    # ------------------------------------------------------------------------------------------------------

    @app.post('/board')
    def client_add_received():
        '''Adds a new element to the board
        Called directly when a user is doing a POST request on /board'''
        global board, node_id
        try:
            # Retrieve the entry from the form
            new_entry = request.forms.get('entry')
            payload = {'entry': new_entry}
            if leader_id == node_id:
                element_id = board.add(new_entry)
                # Get the id from the board and make sure everything went ok.
                # Propagate the new entry to none leader vessels
                if (element_id < 0):
                    return format_response(500, 'Failed to create new entry')
                propagate_to_vessels(ACTION_CONSTANT_ADD, element_id, payload)
                return format_response(200)
            else:
                propagate_to_leader(
                    ACTION_CONSTANT_ADD, board.get_seq_num(), payload)
                return format_response(200)

        except Exception as e:
            print e
        return format_response(400)

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        global board, node_id
        # Try to retrieve the delete field from the form and cast to int.
        delete_or_modify = None
        try:
            delete_or_modify = int(request.forms.get('delete'))
        except Exception as e:
            print(e)
            return format_response(400, 'Could not parse delete status from form')

        # Try to retrieve the entry from the form.
        entry = request.forms.get('entry')
        if (entry == None):
            return format_response(400, 'Form needs to contain entry')

        # Make sure we have the delete_or_modify field retrieved.
        if (delete_or_modify != None):
            # Modify code
            if delete_or_modify == 0:
                payload = {'entry': entry}
                if leader_id == node_id:
                    # Modify and propagate modify to other vessels.
                    board.modify(element_id, entry)
                    propagate_to_vessels(ACTION_CONSTANT_MODIFY, element_id, payload)
                    return format_response(200)
                else:
                    # Notify leader of modify event
                    propagate_to_leader(ACTION_CONSTANT_MODIFY, element_id, payload)
                    return format_response(200)

            # Delete code
            if delete_or_modify == 1:
                if leader_id == node_id:
                    # Delete and propagate to other vessels.
                    board.delete(element_id)
                    propagate_to_vessels(ACTION_CONSTANT_DELETE, element_id)
                    return format_response(200)
                else:
                    propagate_to_leader(ACTION_CONSTANT_DELETE, element_id)
                    return format_response(200)
        return format_response(400, 'Invalid delete status, should be either 0 or 1')

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        global node_id
        # Try to parse the element_id as an int.
        try:
            element_id = int(element_id)
        except Exception as e:
            print e
            return format_response(400, 'Element id needs to be an integer')
        # Add or Modify action
        if (action in [ACTION_CONSTANT_ADD, ACTION_CONSTANT_MODIFY]):
            # Try to retrieve entry from propagation
            entry = None
            try:
                json_dict = request.json
                entry = json_dict.get('entry')

            except Exception as e:
                # Can't parse entry from response
                print e
                return format_response(400, 'Could not retrieve entry from json')

            # Make sure we have an entry
            if (entry == None):
                print 'Entry none'

            payload = {'entry': entry}
            if (action == ACTION_CONSTANT_ADD):
                print 'Adding element'
                board.add(entry)

                if leader_id == node_id:
                    print 'Propagate add to none leaders'
                    propagate_to_vessels(ACTION_CONSTANT_ADD, element_id, payload)

                return format_response(200)
            if (action == ACTION_CONSTANT_MODIFY):
                print 'Modify element'
                board.modify(element_id, entry)

                if leader_id == node_id:
                    print 'Propagate modify to none leaders'
                    propagate_to_vessels(ACTION_CONSTANT_MODIFY, element_id, payload)
                return format_response(200)
        # Delete action
        if (action == ACTION_CONSTANT_DELETE):
            board.delete(element_id)
            print 'Delete element'

            if leader_id == node_id:
                print 'Propagate delete to none leaders'
                propagate_to_vessels(ACTION_CONSTANT_DELETE, element_id)

            return format_response(200)
        return format_response(400, 'Not a valid action')

    # Leader propagation received
    @app.post('/pick/leader/<sender_id>')
    def leader_propagation_received(sender_id):
        global node_id, leader_id, leader_rand 
        max_value = None
        max_node_id = None
        try:
            json_dict = request.json
            max_value = json_dict.get('max_value')
            max_node_id = json_dict.get('max_node_id')
            org_sender_id = json_dict.get('org_sender_id')

        except Exception as e:
            # Can't parse entry from response
            print e
            return format_response(400, 'Could not retrieve entry from json')

        if (org_sender_id == node_id):# Got back to me; election done; new leader elected 
            leader_id = max_node_id
            leader_rand = max_value
            print ('Got the leader; Leader Id is: {}'.format(leader_id))
            return format_response(200)
        else:
            if (rand_value > max_value):
                max_value = rand_value
                max_node_id = node_id
            elif (rand_value == max_value and node_id > max_node_id):
                max_value = rand_value
                max_node_id = node_id
            
            payload = {'max_value': max_value,
                       'max_node_id': max_node_id, 'org_sender_id': org_sender_id}
            send_election_call_to_next_vessel(sender_id, payload)
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
    # Execute the code

    def main():
        global vessel_list, node_id, app
        port = 80
        parser = argparse.ArgumentParser(
            description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid',
                            default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1,
                            type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        vessel_list = dict()
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv + 1):
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        try:
            t = Thread(target=run, kwargs=dict(
                app=app, host=vessel_list[str(node_id)], port=port))
            # t.daemon = True # we do not wnat to run it in the backgorund
            t.start()
            time.sleep(2)
            #run(app, host=vessel_list[str(node_id)], port=port)
            start_leader_election(node_id)
        except Exception as e:
            traceback.print_exc()
            print 'error'
            print e
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
    traceback.print_exc()
    while True:
        time.sleep(60.)


