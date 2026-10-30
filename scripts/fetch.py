import json,urllib.request,urllib.error,time,sys,os
def get(path):
    for a in range(4):
        pass
    for a in range(4):
        try:
            with urllib.request.urlopen("https://api.openf1.org/v1/"+path,timeout=90) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code==404: return None
            print("retry",path,e,file=sys.stderr); time.sleep(2+a*3)
        except Exception as e:
            print("retry",path,e,file=sys.stderr); time.sleep(2+a*3)
    return None
sk=int(sys.argv[1]); d=f"raw/{sk}"; os.makedirs(d,exist_ok=True)
for ep in ["drivers","laps","position","stints","pit","race_control","team_radio","weather","session_result","overtakes"]:
    f=f"{d}/{ep}.json"
    if os.path.exists(f): continue
    r=get(f"{ep}?session_key={sk}")
    json.dump(r,open(f,"w")); print(ep, None if r is None else (len(r) if isinstance(r,list) else r)); time.sleep(.4)
