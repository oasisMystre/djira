from socketio.client import Client

client = Client()
client.connect("http://localhost:8000")


@client.on("connect")
def on_data(payload):
    client.send({
        "method": "POST", 
        "namespace": "users",
        "action": "subscribe",
        "data": {}
    })



@client.on("message")
def on_message(payload):
    pass

