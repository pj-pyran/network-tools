"""
Command line tool to continually monitor your wifi/ethernet connection via a ping to
google DNS (8.8.8.8).
Default ping frequency = 1 per second.
If ping to google fails continually, script will switch mode to monitor your connection
to router as well as google. If router connection successful, it will switch back to
only pinging google.
"""
import argparse
import subprocess
from time import sleep
import warnings

# Create an ArgumentParser object
parser = argparse.ArgumentParser()

# Add arguments
parser.add_argument('--pf', type=float, help='Ping frequency', default=1)
parser.add_argument('--a', type=str, help='Address', default='8.8.8.8')
# parser.add_argument('--arg2', type=str, default='default_value', help='Description of arg2')
# Parse the arguments
args = parser.parse_args()
# Access the parsed arguments
retry_interval_sec = args.pf
address = args.a

pings_to_try = float('inf')
# No. pings to try on the router. If all successful, will switch back to pinging only address above
SWITCHBACK_THRESHOLD = 10
# Characters used to show connection status
UP_CHARACTER = '■'
DOWN_CHARACTER = '.'


def monitor_connection(n_pinged_, address_='8.8.8.8', retry_interval_sec_=retry_interval_sec,
                       up_character_=UP_CHARACTER, down_character_=DOWN_CHARACTER):
    out = subprocess.Popen(['ping', address_, '-c', '1'],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.STDOUT)
    sleep(retry_interval_sec_)
    character_fill = 79
    char = '+' if n_pinged_ % 2 == 0 else '-'
    if out.poll() is None or out.poll() != 0:
        print(f'{char} {character_fill*down_character_}\r')
        return False, n_pinged_+1
    else:
        print(f'{char} {character_fill*up_character_}\r')
        return True, n_pinged_+1


def monitor_server_router(n_pinged_, router='192.168.0.1', server='8.8.8.8',
                          retry_interval_sec_=retry_interval_sec, up_character_server=UP_CHARACTER,
                          up_character_router=UP_CHARACTER, down_character_=DOWN_CHARACTER):
    """
    Monitors both the router and server at the same time and prints a bar string split in half to
    show state of each.
    Returns the state of each as well as number of pings done
    """
    out_router = subprocess.Popen(['ping', router, '-c', '1'],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.STDOUT)
    out_server = subprocess.Popen(['ping', server, '-c', '1'],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.STDOUT)
    sleep(retry_interval_sec_)

    character_fill = 80
    # Is the router reachable?
    if out_router.poll() is None or out_router.poll() != 0:
        router_string = int((character_fill/2) - 1)*down_character_
        router_up = False
    else:
        router_string = int((character_fill/2) - 1)*up_character_router
        router_up = True

    # Is the server reachable?
    if out_server.poll() is None or out_server.poll() != 0:
        server_string = int((character_fill/2) - 1)*down_character_
        server_up = False
    else:
        server_string = int((character_fill/2) - 1)*up_character_server
        server_up = True
    char = '+' if n_pinged_ % 2 == 0 else '-'
    print(' '.join([char, router_string, server_string]))
    return router_up, server_up, n_pinged_+1


def get_router_address():
    out = subprocess.check_output('netstat -nr|grep default', shell=True).splitlines()[0]
    out = str(out).splitlines()[0]
    router_address_ = out.split('        ')[1].strip()
    if len(router_address_.split('.')) != 4:
        default_router = '192.168.0.1'
        error_string = f'[WARN] Unexpected router IP Address "{router_address_}" found;'
        error_string += f' defaulting to "{default_router}"'
        warnings.warn(error_string)
        return default_router
    else:
        print(f'[INFO] Found router address {router_address_}')
        return router_address_



if __name__=='__main__':
    down_consecutive, n_pinged = 0, 0
    while n_pinged < pings_to_try:
        # Get the info on connection up/down
        connection_up, n_pinged = monitor_connection(n_pinged, address, retry_interval_sec)
        # If up then reset down counter
        if connection_up:
            down_consecutive = 0

        # If down then increment down counter
        else:
            down_consecutive += 1
            # If down 5 times in a row then check router connection
            if down_consecutive==5:
                print('[INFO] checking access to router....')
                # Set vars to begin router check. router_up_consecutive counts successful
                # consecutive router connections, monitoring will switch back to server IP after
                # SWITCHBACK_THRESHOLD successful router pings.
                router_address, router_access, router_up_consecutive = get_router_address(), False, 0

                while n_pinged < pings_to_try and (not router_access or router_up_consecutive < SWITCHBACK_THRESHOLD):
                    router_access, server_access, n_pinged = monitor_server_router(n_pinged, router=router_address, retry_interval_sec_=retry_interval_sec)
                    if router_access:
                        router_up_consecutive += 1
                        if router_up_consecutive == SWITCHBACK_THRESHOLD:
                            msg = '[INFO] Connection stable to router; switching back to monitoring '
                            print(msg + address)
                    else:
                        router_up_consecutive = 0
    