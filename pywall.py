#!/usr/bin/env python2

import os
import sys
import time
import signal

import json
import urllib2

run = True

formats = { 'reset'     : '\033[00m',
            'mention'   : '\033[00;34m',
            'hashtag'   : '\033[01;37m',
            'url'       : '\033[04;34m',
            'from_user' : '\033[01;31m',
            }

def usage(prog):
    print('Usage: %s <hashtag>' % prog)

def handler(signum, frame):
    global run
    run = False

def wrap(text, columns, startlen = 0):
    words = text.split()
    out = ''
    l = startlen
    for i in range(len(words)):
        if l + len(words[i]) >= columns:
            out += '\n'
            l = 0
        else:
            l += 1
            out += ' '
        l += len(words[i])
        out += words[i]

    return out

def get_term_size():
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh',
                               fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except:
            return None
        return cr

    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)

    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass

    if not cr:
        if os.environ.has_key('LINES') and os.environ.has_key('COLUMNS'):
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        else:
            cr = (25, 80)

    return int(cr[1]), int(cr[0])


def format_tweet(tweet, columns):
    # unfortunately I'm so stupid and lazy I don't want to use
    # indices, so let's just slow it down by string replacements
    text = tweet['text']
    for url in tweet['entities']['urls']:
        text = text.replace(url['url'], url['display_url'])

    text = wrap(text, columns, len(tweet['from_user']) + len('@: '))

    for mention in tweet['entities']['user_mentions']:
        text = text.replace('@%s' % mention['screen_name'],
                     '%s@%s%s' % (formats['mention'], mention['screen_name'], formats['reset']))

    for hashtag in tweet['entities']['hashtags']:
        text = text.replace('#%s' % hashtag['text'],
                     '%s#%s%s' % (formats['hashtag'], hashtag['text'], formats['reset']))

    for url in tweet['entities']['urls']:
        text = text.replace(url['display_url'],
                     '%s%s%s' % (formats['url'], url['display_url'], formats['reset']))

    text = '%s@%s:%s %s' % (formats['from_user'], tweet['from_user'], formats['reset'], text)

    return text

def main(argv):
    global run

    if len(argv) is not 2:
        usage(argv[0])
        return 1

    columns = get_term_size()[0]

    url = 'http://search.twitter.com/search.json'
    query = '?q=%s' % urllib2.quote(argv[1])
    options = '&include_entities=true'

    for sig in (signal.SIGUSR1, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handler)

    while run:
        texts = []
        while query:
            try:
                data = json.load(urllib2.urlopen(url + query + options))
                texts += [format_tweet(tweet, columns) for tweet in data['results']]
            except (urllib2.HTTPError, urllib2.URLError):
                continue

            if data.has_key('next_page'):
                query = data['next_page']
            else:
                query = False

        for text in reversed(texts):
            print('\n%s' % text)

        query = data['refresh_url']

        time.sleep(10)

    return 0

if __name__ == "__main__":
    exit(main(sys.argv))
