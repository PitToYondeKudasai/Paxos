#!/usr/bin/env python

import sys
import socket
import time
import struct
import time
import json
from numpy import ceil
from collections import Counter
from itertools import chain

# GLOBAL VARIABLES

timeout_message = 0.01
timeout_quorum = 0.01
n_acceptors = 3
n_learners = 2
n_proposers = 2
Qa = int(ceil((n_acceptors+1)/2))
msg_length = 2**16
n_instances_BD = 100
faulty_acceptors = 0

# UTILITY FUNCTIONS

def mcast_receiver(hostport):
  """create a multicast socket listening to the address"""
  recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
  recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  recv_sock.bind(hostport)

  mcast_group = struct.pack("4sl", socket.inet_aton(hostport[0]), socket.INADDR_ANY)
  recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mcast_group)
  return recv_sock


def mcast_sender():
  """create a udp socket"""
  send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
  return send_sock


def parse_cfg(cfgpath):
  cfg = {}
  with open(cfgpath, 'r') as cfgfile:
    for line in cfgfile:
      (role, host, port) = line.split()
      cfg[role] = (host, int(port))
  return cfg


# ----------------------------------------------------

def send_request(s):
    s.sendto(encode(['request_hist']), config['acceptors'])

def send_p1a(s, sending_code):
    s.sendto(encode(['p1a', sending_code]), config['acceptors'])

def send_p1b(s, sending_code, v_rnd, v_val):
    s.sendto(encode(['p1b', sending_code, v_rnd, v_val]), config['proposers'])

def send_p2a(s, sending_code, c_val):
    s.sendto(encode(['p2a', sending_code, c_val]), config['acceptors'])

def send_p2b(s, sending_code, v_rnd, v_val):
    s.sendto(encode(['p2b', sending_code, v_rnd, v_val]), config['proposers'])

def send_decision_to_learners(s, sending_code, v_val):
    s.sendto(encode(['decide', sending_code, v_val]), config['learners'])

def reset_vals(s, n_instance, c_rnd):
    sending_code = create_sending_code(n_instance,c_rnd)
    s.sendto(encode(['reset', sending_code]), config['acceptors'])

def send_hist_list(s, id, hist_list):
    s.sendto(encode(['hist_list',id, hist_list]), config['learners'])

def unpack_dict(params):
  return (params['state'],
          params['instance'],
          params['id'],
          params['rnd'],
          params['clients_values'],
          params['proposed_value'],
          params['my_value'],
          params['socket_s'],
          params['socket_r']
          )


def create_sending_code(n_instance, rnd, id = 0):
  if type(rnd) == int:
    return str(n_instance) + '.' + str(rnd) + '.' + str(id)
  else:
    return str(n_instance) + '.' + str(rnd)


def str_to_num(n):
  try:
    a = int(n)
  except:
    try:
      a = float(n)
    except:
      a = None
  return a


def choose_val(v_rnds, v_vals, params):
    f = lambda i: v_rnds[i]
    maximum = max(range(len(v_rnds)), key = f)
    c_val = v_vals[maximum]
    if c_val != None:
      params['proposed_value'] = c_val
      params['my_value'] = False
      return params
    else:
        params['proposed_value'] = params['clients_values'][0]
        params['my_value'] = True
    return params


def encode(msg):
  return ';'.join(list(map(lambda x: str(x), msg)))


def decode(msg):
    msg = msg.split(';')

    if msg[0] == 'hist_list':
        return [msg[0],eval(msg[1]),eval(msg[2])]
    elif msg[0] == 'request_hist':
        return [msg[0]]
    else:
        n_instance, rnd, id = msg[1].split('.')
        c_rnd = float('.'.join([rnd,id]))
        return [msg[0], int(n_instance), c_rnd] + list(map(lambda x: str_to_num(x), msg[2:]))


def p1b(params):
  s = params['s']
  hist_list = params['hist_list']
  msg_list =  params['msg_list']

  prop_instance, c_rnd = msg_list[1], msg_list[2]
  if prop_instance in hist_list.keys():
    rnd,v_rnd,v_val = hist_list[prop_instance]
    if rnd<c_rnd:
        rnd=c_rnd
        hist_list[prop_instance][0]=c_rnd
    else:
      params['hist_list'] = hist_list
      return params
  else:
    rnd = c_rnd
    v_rnd = 0
    v_val = None
    hist_list[prop_instance]=[rnd, v_rnd, v_val]

  sending_code = create_sending_code(prop_instance, c_rnd)
  send_p1b(s, sending_code, v_rnd, v_val)
  params['hist_list'] = hist_list
  return params


def p2b(params):
  s = params['s']
  hist_list = params['hist_list']
  msg_list =  params['msg_list']
  prop_instance, c_rnd = msg_list[1], msg_list[2]
  if prop_instance in hist_list.keys():
    rnd, _,_ = hist_list[prop_instance]
    if c_rnd >= rnd:
      v_rnd = c_rnd
      v_val = msg_list[3]
      hist_list[prop_instance] = [c_rnd, v_rnd, v_val]
    else:
      params['hist_list'] = hist_list
      return params
  else:
     v_rnd = c_rnd
     v_val = msg_list[3]
     hist_list[prop_instance]=[c_rnd, v_rnd, v_val]

  sending_code = create_sending_code(prop_instance, c_rnd)
  send_p2b(s, sending_code, v_rnd, v_val)
  params['hist_list'] = hist_list
  return params


def request(params):
  s = params['s']
  hist_list = params['hist_list']
  id =  params['id']
  send_hist_list(s,id,hist_list)
  return(params)


def listen_clients(params):
  while True:
    r = params["socket_r"]
    try:
      msg = r.recv(msg_length )
      msg_list = decode(msg)
      if msg_list[0] == 'client val':
          params["clients_values"].append(msg_list[1])
          params["state"] = "send_p1a"
          return(params)
    except socket.timeout:
      continue


def p1a(params):
  if len(params["clients_values"]) == 0:
    params['state'] = 'init'
    return(params)
  params['rnd']+=1

  _, n_instance, id, rnd,_,_,_,s,_ = unpack_dict(params)
  sending_code = create_sending_code(n_instance, rnd, id)
  send_p1a(s, sending_code)
  params["state"]="waiting_p1b"
  return params


def waiting_p1b(params):
  v_vals = []
  v_rnds = []
  _, n_instance, id, rnd,_,_,_,_,r = unpack_dict(params)
  c_rnd = float(str(rnd) + '.' + str(id))

  start = time.time()
  while (len(v_vals) < Qa) and (time.time() - start < timeout_quorum):
    try:
        msg = r.recv(msg_length)
        msg_list = decode(msg)
        if msg_list[0] == 'client val':
            params['clients_values'].append(msg_list[1])
        elif msg_list[0] == 'p1b':
          if msg_list[1] == n_instance and msg_list[2] == c_rnd:
              v_vals.append(msg_list[4])
              v_rnds.append(msg_list[3])
          elif msg_list[1] > n_instance:
              params['instance'] = msg_list[1]
              params['state'] = "send_p1a"
              return(params)
    except socket.timeout:
            continue

  if len(v_vals) >= Qa:
      params = choose_val(v_rnds, v_vals, params)
      params['state'] = "send_p2a"
  else:
      params['state'] = "send_p1a"
      params['rnd'] += 1
  return(params)


def p2a(params):
  _,n_instance,id,rnd,_,c_val,_,s,_ = unpack_dict(params)
  sending_code = create_sending_code(n_instance, rnd, id)
  send_p2a(s, sending_code, c_val)
  params["state"]="waiting_p2b"
  return(params)


def waiting_p2b(params):
  _, n_instance, id, rnd, clients_values, _, my_value,_,r = unpack_dict(params)
  c_rnd = float(str(rnd) + '.' + str(id))
  sending_code = create_sending_code(n_instance, rnd, id)
  start = time.time()
  Q = 0
  while (Q < Qa) and (time.time() - start < timeout_quorum):
    try:
      msg = r.recv(msg_length)
      msg_list = decode(msg)
    except socket.timeout:
      continue
    if msg_list[0] == 'client val':
      params['clients_values'].append(msg_list[1])
    elif (msg_list[0] == 'p2b'):
      if (msg_list[1] == n_instance) and (msg_list[2] == c_rnd):
        Q += 1
      elif msg_list[1] > n_instance:
        params['instance'] = msg_list[1]
        params['state'] = "send_p1a"
        return(params)

  if Q >= Qa:
    params['state'] = "send_decision"
    if my_value == True:
      params["clients_values"] = params["clients_values"][1:]
      params["my_value"] = False
  else:
    params['state'] = "send_p1a"
  return params


def send_decision(params):
  _, n_instance, id, rnd, _, v_val, _,s,_ = unpack_dict(params)
  sending_code = create_sending_code(n_instance, rnd, id)
  send_decision_to_learners(s, sending_code, v_val)
  params['state'] = "send_p1a"
  params["instance"] += 1
  return params

def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z


def aggregate_decisions(params):
    acceptors_hist = []
    for decision_dic in params['received'].values():
        acceptors_hist.append(decision_dic)
    decisions = params['decisions']
    value_list = []
    for idx in range(len(acceptors_hist)):
      value_list.extend([str(k) + "-" + str(v[2]) for k,v in acceptors_hist[idx].items() ])
    filtered_values = [k for k, v in Counter(value_list).items() if v >= Qa]
    g = [[int(i) for i in k.split("-")] for k in filtered_values ]
    params['decisions'] = merge_two_dicts(dict(g), decisions)
    return(params)

def decision_to_list(params,msg_list):
  msg_type, n_instance, c_rnd, val=msg_list
  params["decisions"][int(n_instance)] = val
  return(params)

def recontruct_decisions(params, msg_list):
    acceptor_id = msg_list[1]
    acceptor_hist = msg_list[2]
    if not(acceptor_id in params["received"].keys()):
        params["received"][acceptor_id] = acceptor_hist
    if len(params["received"].keys())>=Qa:
        params = aggregate_decisions(params)
    return(params)

def printvals(params):
    decisions=params['decisions']
    counter=params['counter']
    if counter in decisions.keys():
        print(decisions[counter])
        counter += 1
        params['counter'] = counter
    return params

#------ ROLES ------#

def acceptor(config, id):
  print '-> acceptor', id

  r = mcast_receiver(config['acceptors'])
  s = mcast_sender()

  hist_list = {}

  actions = {"p1a": p1b,
             "p2a" : p2b,
             "request_hist" : request,
            }

  params={'s' : s,
          'hist_list' : hist_list,
          'msg_list' : [],
          'id' : id,
          'state': 'Alive'
  }
  while params['state'] == 'Alive':
    msg = r.recv(msg_length)
    msg_list = decode(msg)
    params['msg_list'] = msg_list
    if msg_list[0] in actions.keys():
      params = actions[msg_list[0]](params)
    else:
      pass
    if (len(params['hist_list'].keys()) > n_instances_BD * id) and (id <= faulty_acceptors):
        print(id, 'Dead')
        print(len(params['hist_list'].keys()))
        params['state'] = 'Dead'


def proposer(config, id):
  print '-> proposer', id
  r = mcast_receiver(config['proposers'])
  s = mcast_sender()
  r.settimeout(timeout_message)

  params = {
      'state' : "init",
      'instance' : 1,
      'id' : id,
      'rnd' : 0,
      'clients_values' : [],
      "proposed_value" : "None",
      'my_value' : False,
      'socket_s' : s,
      'socket_r' : r
  }

  actions = {"init": listen_clients,
             "send_p1a" : p1a,
             "waiting_p1b" : waiting_p1b,
             "send_p2a": p2a,
             "waiting_p2b" : waiting_p2b,
             "send_decision" : send_decision
            }

  if id==1:
    while True:
      params=actions[params["state"]](params)


def learner(config, id):
  r = mcast_receiver(config['learners'])
  s = mcast_sender()
  r.settimeout(timeout_message)
  send_request(s)
  params = {
           'decisions' : {},
           'counter' : 1,
           'received' : {},
           'learner_id' : id
           }

  actions = {"hist_list": recontruct_decisions,
             "decide" : decision_to_list
            }

  while True:
    try:
      msg = r.recv(msg_length)
      msg_list = decode(msg)

      params = actions[msg_list[0]](params, msg_list)
      sys.stdout.flush()
    except socket.timeout:
      params = printvals(params)
      sys.stdout.flush()
      pass

    params = printvals(params)
    sys.stdout.flush()

def client(config, id):
  print '-> client ', id
  s = mcast_sender() # Creation socket
  for value in sys.stdin:
    value = value.strip()
    print("client: sending %s to proposers" % (value))
    value_send = create_sending_code(value, 0)
    msg = encode(['client val', value_send])
    s.sendto(msg, config['proposers'])
  print('client done.')

#------ MAIN ------#

if __name__ == '__main__':
  cfgpath = sys.argv[1]
  config = parse_cfg(cfgpath)
  role = sys.argv[2]
  id = int(sys.argv[3])
  if role == 'acceptor':
    rolefunc = acceptor
  elif role == 'proposer':
    rolefunc = proposer
  elif role == 'learner':
    rolefunc = learner
  elif role == 'client':
    rolefunc = client
  rolefunc(config, id)
