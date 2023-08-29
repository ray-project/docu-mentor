import requests
   
# Service specific config
base_url = "https://ray-assistant-bxauk.cld-kvedzwag2qa8i5bj.s.anyscaleuserdata.com"
token = "TFqAspmzH5w_L_CiAfBVLVZ3pCKCx2KPImE70YLxwiA"
   

# Requests config
full_url = f"{base_url}/query"
headers = {"Authorization": f"Bearer {token}"}
   

# resp = requests.post(full_url, headers=headers, json={"query": "What is Ray?"})
# print(resp.content)
   

s = requests.Session()

with s.post(full_url, headers=headers, json={"query": "What is Ray?"}, stream=True) as resp:
    for line in resp.iter_lines():
        if line:
            print(line)

