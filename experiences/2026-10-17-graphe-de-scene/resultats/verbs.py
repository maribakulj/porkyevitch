import json, re, collections
recs=[]
for f in ['train','val','test']:
    recs+=json.load(open(f'raw/{f}.json'))
texts=[v['description'] for r in recs for v in r['objects'].values()]
# lexique fermé : prépositions relationnelles + verbes d'interaction (formes fléchies incluses)
PREP={'with','on','in','at','to','by','between','behind','before','beside','under','over','from','toward','towards','through','into','around','among','against','near','above','below','beneath','upon','within','beyond','across','along','alongside','inside','outside','without','of','for'}
VERB={'holds','hold','held','holding','looks','look','looking','looked','kneels','kneel','kneeling','knelt','embraces','embrace','embracing','embraced','kiss','kisses','kissing','crowns','crown','crowning','blesses','bless','blessing','presents','presenting','presented','wears','wear','wearing','worn','hides','hiding','hidden','leads','lead','leading','chases','chase','chasing','offers','offering','receives','receiving','received','sits','sit','sitting','stands','standing','rests','resting','reaches','reaching','extends','extending','kills','killing','killed','supports','supported','supporting','places','placing','placed','carries','carrying','carried','points','pointing','pointed','gazes','gazing','gazed','watches','watching','serenades','serenading','turns','turning','turned','faces','facing','faced','surrounds','surrounded','surrounding','greets','greeting','bids','attends','attending','rides','riding','riding','plays','playing','played','reads','reading','read','drinks','drinking','eats','eating','pours','pouring','wrestles','wrestling','lies','lying','lay','leans','leaning','cling','clings','clinging','touches','touching','touched','holds'}
c=collections.Counter(); total=0
for t in texts:
    for w in re.findall(r"[a-zA-Z]+", t.lower()):
        if w in PREP or w in VERB:
            c[w]+=1; total+=1
print('entities',len(texts),'occurrences',total)
for w,n in c.most_common(30): print(f'{w}\t{n}')
