# This example requires the 'message_content' intent.
import discord
import requests
import os
import logging
import redis

log = logging.getLogger(__name__)
redis_client = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            decode_responses=True)

class DiscordClient(discord.Client):

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)
    
    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        channel = message.channel

        if str.lower(message.content) == 'cancel':

            if str(self.user.id) == str(os.environ.get('SUB_BOT_ID')):
                url = os.environ.get('SUB_API_URI') + '/api/v1/plan/check/'+str(message.author.id)
                headers = {'content-type': 'application/json',
                        'accept': 'application/json',
                        'Authorization': 'Sub '+os.environ.get('SUB_API_KEY')
                        }
                
                resp = requests.get(url=url, headers=headers)
                print("get subscription:", resp.json())



                item = resp.json()
                if 'data' in item and 'status' in item['data'] and item['data']['status']:
                    message_error = item['message'] if 'message' in item else 'Please subscribe to a plan.'

                    await channel.send(message_error)

                elif 'subscription_id' in item:

                    subscription_id = item['subscription_id']
                    discord_userid = item['discord_userid']
                    nonce = item['nonce']

                    redis_client.set("subscription_id_" + str(message.author.id), subscription_id)
                    redis_client.set("discord_userid_" + str(message.author.id), discord_userid)
                    redis_client.set("nonce_" + str(message.author.id), nonce)

                    redis_client.set("cancel_" + str(subscription_id)+ "_" +str(discord_userid), 1)

                    message_confirm = item['message'] if 'message' in item else 'If you cancel your subscription, you will lose access to the Discord room with admins. Are you certain you want to proceed with the cancellation? Yes or No'

                    await channel.send(message_confirm)

        def check(m):
            subscription_id = redis_client.get("subscription_id_" + str(m.author.id))
            if (str.lower(m.content) == 'no' and str(self.user.id) == str(os.environ.get('SUB_BOT_ID')) and subscription_id):
                redis_client.delete("subscription_id_" + str(message.author.id))
                redis_client.delete("discord_userid_" + str(message.author.id))
                redis_client.delete("nonce_" + str(message.author.id))
                discord_userid = redis_client.get("discord_userid_" + str(m.author.id))
                redis_client.delete("cancel_" + str(subscription_id)+ "_" +str(discord_userid))

            return str.lower(m.content) == 'yes' and str(self.user.id) == str(os.environ.get('SUB_BOT_ID')) and subscription_id

        msg = await self.wait_for('message', check=check)
        if msg:
            
            subscription_id = redis_client.get("subscription_id_" + str(message.author.id))
            discord_userid = redis_client.get("discord_userid_" + str(message.author.id))
            nonce = redis_client.get("nonce_" + str(message.author.id))
            
            count_plan = redis_client.get("cancel_" + str(subscription_id)+ "_" +str(discord_userid))
            if (not count_plan or int(count_plan) > 1):
                if count_plan:
                    redis_client.set("cancel_" + str(subscription_id)+ "_" +str(discord_userid), int(count_plan)+1)
                
                return
            
            url = os.environ.get('SUB_API_URI') + '/api/v1/plan/cancel/'+str(subscription_id)
            headers = {'content-type': 'application/json',
                    'accept': 'application/json',
                    'Authorization': 'Sub '+os.environ.get('SUB_API_KEY'),
                    'HTTP_X_WP_NONCE': nonce
                }
            
            data = {'discord_userid': discord_userid}
            resp = requests.post(url=url, json=data, headers=headers)
            
            item = resp.json()

            if 'data' in item and 'status' in item['data'] and item['data']['status']:
                message_error = item['message']

                redis_client.delete("cancel_" + str(subscription_id)+ "_" +str(discord_userid))

                await channel.send(message_error)

                redis_client.delete("subscription_id_" + str(message.author.id))
                redis_client.delete("discord_userid_" + str(message.author.id))
                redis_client.delete("nonce_" + str(message.author.id))

            elif 'message' in item:
                message_confirm = item['message']

                redis_client.delete("cancel_" + str(subscription_id)+ "_" +str(discord_userid))
                
                await channel.send(message_confirm)
            
                redis_client.delete("subscription_id_" + str(message.author.id))
                redis_client.delete("discord_userid_" + str(message.author.id))
                redis_client.delete("nonce_" + str(message.author.id))

def run_bot(nonce):
    try:
        intents = discord.Intents.default()
        intents.message_content = True
        client = DiscordClient(intents=intents)
        token = os.environ.get('SUB_BOT_TOKEN')
        client.run(token)

        url = os.environ.get('SUB_API_URI') + 'api/v1/plan/update-bot'
        headers = {'content-type': 'application/json',
                'accept': 'application/json',
                'Authorization': 'Sub '+os.environ.get('SUB_API_KEY'),
                'HTTP_X_WP_NONCE': nonce
            }
        
        resp = requests.post(url=url, headers=headers)
        print("update run bot:", resp.json())

    except AssertionError as e:
        log.exception(e)
    except Exception as e:
        log.exception(e)
