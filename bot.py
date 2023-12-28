#imports
from mcrcon import MCRcon as rcon
from discord.ext import commands
from mcstatus import JavaServer
import discord
import json
import os
import time
import asyncio

#gcloud api
#sudo snap install --classic google-cloud-cli
#pip install google-cloud-compute
from google.cloud import compute_v1

#===============================================================

global SETTINGS

#discord

#discord settings
intents = discord.Intents.all()
client = commands.Bot(command_prefix = '$',intents=intents)

#run when bot is ready
@client.event
async def on_ready():
    global IP_MAPPING


    try:
        with open("ips.json","r") as file:
            IP_MAPPING = json.load(file)
            print(IP_MAPPING)
    except FileNotFoundError as e:
        servList, fservList = checkServerList()
        for i in servList:
            IP_MAPPING[i] = None
        with open("ips.json","w") as file:
            json.dump(IP_MAPPING,file)
    except Exception as e:
        print(f'unknown exception: {e}')
        exit(1)

    print("im ready!")

@client.command()
async def mc(ctx, arg1=None, arg2=None, arg3=None, arg4=None):
    '''
    this function is use for accepting minecraft discord command
    seperate into 2 parts: normal user, and admin
    functions for normal user are:
    start [servername] - start the server
    list - list all the server
    help - help command
    set [servername] [ip] - set ip for specific server
    player [servername] - get player status on server
    whitelist [add/list] [servername]  - add/view whitelist on server
    '''
    global SETTINGS
    try:
        print(f'{arg1} {arg2} {arg3} {arg4}')
        match arg1:
            case 'start':
                await ctx.send('starting server...',silent=True)
                await ctx.reply(startServer(arg2))

            case 'ip':
                await ctx.send("getting server list...",silent=True)
                ufServList, fServList = checkServerList()
                await ctx.reply(fServList,silent=True)

            case 'help':
                await ctx.reply("imma make help later, but for the time being, pls ask poly_",silent=True)

            case 'set':
                if arg2 is not None:
                    if arg3 is not None:
                        await ctx.reply(mapIpToServer(arg2, arg3),silent=True)
                    else:
                        await ctx.send('invalid ip.',silent=True)
                else:
                    await ctx.send('wrong argument.',silent=True)

            case 'player':
                player, status = getPlayer(arg2)
                if status > -1: 
                    await ctx.send(player,silent=True)

            case 'whitelist':
                whitelist_list = whitelist(arg2, arg3, arg4)
                await ctx.reply(whitelist_list)

            #default case
            case None:
                await ctx.send('No command found, plase use "$mc help" to know some shit duh.',silent=True)

            case _:
                await ctx.send(f"command \"{arg2}\" not found, plase use \"$mc help\" to know some shit duh.",silent=True)
                
    except Exception as e:
        print(f'Error: {e}')
        await ctx.send(f'{e}',silent=True)

#===============================================================

#server function

#for mapping ip to server
global IP_MAPPING
IP_MAPPING = {}

def checkServerList():
    instance_client = compute_v1.InstancesClient()
    request = compute_v1.AggregatedListInstancesRequest()
    request.project = SETTINGS['GCLOUD_PROJECT_ID']
    agg_list = instance_client.aggregated_list(request=request)

    raw_serverlist = {}
    for zone, response in agg_list:
         if response.instances:
             for instance in response.instances:
                 raw_serverlist[instance.name] = 'online' if instance.status == 'RUNNING' else 'offline'

    formatted_serverlist = ''
    for i in raw_serverlist:
        formatted_serverlist = formatted_serverlist + f'[{i}] '
        if i in IP_MAPPING:
            formatted_serverlist = formatted_serverlist + f' {IP_MAPPING[i]}\n'
        else:
            IP_MAPPING[i] = None
            formatted_serverlist = formatted_serverlist + f'no ip\n'

    return raw_serverlist, formatted_serverlist

def startServer(servername):
    if servername == None:
        return 'missing server name, please use \"$mc help\" for more information.'

    servList, FservList = checkServerList()
    instance_client = compute_v1.InstancesClient()

    if servername in servList:
        if servList[servername] == 'online':
            return 'the server you try to start is already running.'
        else:
            instance_client.start(project=SETTINGS['GCLOUD_PROJECT_ID'],zone=SETTINGS['GCLOUD_PROJECT_ZONE'],instance=servername)
            while getPlayer(servername)[1] < 0:
                print('tesing survival.')
                time.sleep(5)
            task = asyncio.create_task(startServerTimer(servername))
            return f'server \"{servername}\" started successfully!'
    else:
        return f'server \"{servername}\" does not exists.'

def stopServer(servername):
    if servername == None:
        return 'missing server name, please use \"$mc help\" for more information.'

    servList, FservList = checkServerList()
    instance_client = compute_v1.InstancesClient()
    COMMAND = "\"tmux send-keys -t server.0 ENTER \"stop\" ENTER\""
    if servername in servList:
        if servList[servername] == 'offline':
            return f'server you try to stop is not currently running.'
        else:
            os.system(f"gcloud compute ssh {SETTINGS['GCLOUD_NAME']}@{servername} --zone={SETTINGS['GCLOUD_PROJECT_ZONE']} --command {COMMAND}")
            time.sleep(60)
            instance_client.stop(project=SETTINGS['GCLOUD_PROJECT_ID'],zone=SETTINGS['GCLOUD_PROJECT_ZONE'],instance=servername)
            return f'server \"{servername}\" stopped successfully.'
    else:
        return f'server \"{servername}\" does not exists.'

async def startServerTimer(servername):
    TIMEOUT = 200
    TIME_COUNT = 0
    print(f'time started for server {servername}')
    while TIME_COUNT < TIMEOUT:
        if getPlayer(servername)[1] > 0:
            TIME_COUNT = 0
            await asyncio.sleep(10)
            print('there is player')
        else:
            TIME_COUNT = TIME_COUNT + 1
            await asyncio.sleep(1)
            print(f'there is no player {servername}:{TIME_COUNT}')
    print(f'stopping server: {servername}')
    stopServer(servername)

def mapIpToServer(server, ip):
    global IP_MAPPING
    print(f'test: {server in IP_MAPPING}')
    print(IP_MAPPING)
    print(server)
    if server in IP_MAPPING:
        if IP_MAPPING is not None:
            IP_MAPPING[server] = ip
            try:
                with open("ips.json","w") as file:
                    json.dump(IP_MAPPING,file)
            except Exception as e:
                return f'unknow error saving the file: {e}'
            return f'IP of the server \"{server}\" has been set to \"{ip}\"'
        else:
            return 'missing argument.'
    else:
        return 'no server in list with that name.'

def getPlayer(servername):
    '''
    function to get player count on server
    return:
    -1 - error; not set ip, noserver
    0 - noplayer on server
    1 - player on server
    '''
    if IP_MAPPING[servername] is None:
        return 'IP for this server is not set.', -1
    if servername in IP_MAPPING:
        try:
            server = JavaServer.lookup(IP_MAPPING[servername])
            status = server.status()
            if(status.players.online < 1):
                return f"There are no player online.", 0
            else:
                return f"There are {status.players.online} players online.", 1
        except Exception as e:
            return 'error, trying again.',-1
    else:
        return f'server not found' , -1

def whitelist(op, arg3, arg4):
    '''
    this is a function for whitelisting people to the server
    whitelist [operation] [arg3] [arg4]
    add [name] [servername] 
    list [servername]
    '''
    match op:
        case 'list':
            with rcon(host=IP_MAPPING[arg3],password=SETTINGS['RCON_PASSWORD'],port=SETTINGS['RCON_PORT']) as server:
                whitelist_list = server.command('whitelist list')
                return whitelist_list
        case 'add':
            with rcon(host=IP_MAPPING[arg4],password=SETTINGS['RCON_PASSWORD'],port=SETTINGS['RCON_PORT']) as server:
                whitelist_list = server.command(f'whitelist add {arg3}')
                return whitelist_list
        case _:
            return 'Invalid command or argument.'

#===============================================================

#main function
def main():
    global SETTINGS
    try:
        with open('config.json','r') as config:
            SETTINGS = json.load(config)
            print(SETTINGS)
    except Exception as e:
        print(f'unknown exception: {e}')
        exit(1)
    client.run(SETTINGS['DISCORD_KEYS'])

if __name__ == "__main__":
    main()

#===============================================================
