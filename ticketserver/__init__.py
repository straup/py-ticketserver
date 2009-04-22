#!/usr/bin/env python

__package__    = "ticketserver"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/py-ticketserver"
__copyright__  = "Copyright (c) 2009 Aaron Straup Cope. BSD license : http://www.modestmaps.com/license.txt"

import time
import uuid
import shove
import servable
from wsgiref.simple_server import make_server

# http://pypi.python.org/pypi/shove
# http://www.evilchuck.com/2008/02/tell-python-to-shove-it.html

# this works:
# http://servable.appspot.com/
#
# but you still need to comment out line 104:
# http://code.google.com/p/servable/issues/detail?id=1

class ticketserver (servable.Servable) :

    def __init__ (self, **kwargs) :

        if kwargs['store_uri'] :
            self.store = shove.Shove(kwargs['store_uri'])
        else :
            self.store = shove.Shove()

    def start (self, port=8080) :
        httpd = make_server('', port, self.wsgi_app())
        httpd.serve_forever()

    def index (self) :

        return """This is a bare-bones ticket server that runs as a stand-alone HTTP service.

It allows applications to request a new ticket, check the status of an existing
ticket and mark a ticket as completed. It is not sexy. It does not make
ponies. It makes tickets. What you do with them is your business but presumably
you'd use to keep track of long(ish) running tasks so that clients can
periodically poll to see if they've been completed.

It uses the Shove module to provide a variety of backends for storing tickets;
as of this writing only in-memory and Amazon S3 backends are supported.

The interface looks like this:

	http://localhost:8003/get_ticket

        http://localhost:8003/check_ticket?ticket=TICKETID

        http://localhost:8003/mark_ticket_completed?ticket=TICKETID

All calls return plain text. The 'get_ticket' method returns a ticket. The check
ticket returns (UNKNOWN, PENDING, COMPLETED). The 'mark_ticket_completed' method
returns (OK, FAIL).

Ticket IDs are generated as UUIDs and, by default, are purged the first time
they are checked after having been marked as completed.

There is (currently) no authentication model. It's not expected that you'll be
running this on a public-facing host. Buyer beware.
	"""

    index.path = "/$"
    
    def get_ticket (self) :

        u = uuid.uuid4()
        ticket = u.hex

        t = int(time.time())

        status = {'date_start': t, 'date_complete':0}
        
        self.store.setdefault(ticket, status)
        self.store.sync()

        return ticket

    def check_ticket (self, ticket, purge_on_success=1) :

        data = self.store.get(ticket)
        
        if not data :
            return 'UNKNOWN'

        if data['date_complete'] == 0 :
            return 'PENDING'

        if purge_on_success != 0 :
            self.store.pop(ticket)
            self.store.sync()
            
        return 'COMPLETE'

    def mark_ticket_completed (self, ticket) :
        
        data = self.store.get(ticket)

        if not data :
            return 'FAIL'

        data['date_complete'] = int(time.time())

        self.store.update({ticket:data})
        self.store.sync()
        
        return 'OK'
    
if __name__ == '__main__' :

    import optparse    
    import ConfigParser

    parser = optparse.OptionParser()
    
    parser.add_option("-s", "--scheme", dest="scheme", help="", default=None)
    parser.add_option("-p", "--port", dest="port", help="the port to run your ticket server on", default=8003)
    
    parser.add_option("--s3_config", dest="s3_config", help="", default=None)
    parser.add_option("--s3_bucket", dest="s3_bucket", help="", default=None)        

    (opts, args) = parser.parse_args()

    #
    
    uri = None
    label = 'in-memory'
    
    if opts.scheme == 's3' :

        cfg = ConfigParser.ConfigParser()
        cfg.read(opts.s3_config)

        access_key = cfg.get("aws", "access_key")
        secret_key = cfg.get("aws", "secret_key")
        bucket = opts.s3_bucket
        
        uri = "s3://%s:%s@%s" % (access_key, secret_key, bucket)
        label = "S3 backed"
        
    #

    print "starting %s ticketserver" % (label)
    print "documentation is available at http://localhost:%s" % (opts.port)
    print ""

    #
    
    t = ticketserver(store_uri=uri)
    t.start(port=opts.port)
