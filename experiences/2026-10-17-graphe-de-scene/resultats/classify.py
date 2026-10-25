import json, re
recs={}
for f in ['train','val','test']:
    for r in json.load(open(f'raw/{f}.json')): recs[r['id']]=r
s=json.load(open('sample300.json'))
REL=re.compile(r"\b(holds?|held|hold|looks? (at|toward|towards|over|down)|gaz\w+|kneels?|kneeling|embrac\w+|kiss\w*|crowns?|blesses|blessing|bless\w*|points?|pointing|presents?|presenting|wears?|wearing|hides?|cling\w*|lead\w*|chas\w+|hunt\w*|with|and|before|beside|behind|between|among|surrounded|accompan\w+|serenad\w+|offer\w*|receiv\w+|bids?|plays?|playing|reading|sits?|stands?|lies?|rests?|supported|reaches?|extends?|tends?|kills?|killing|beheaded|depict\w* (?:him|her|the))\b", re.I)
out=[]
for i,x in enumerate(s):
    r=recs[x['painting_id']]
    others=[k for k in r['objects'] if k!=x['entity']]
    d=x['description'].lower()
    hit=[k for k in others if len(k)>=4 and any(w in d for w in k.split() if len(w)>=4)]
    rel=bool(REL.search(x['description']))
    out.append(dict(i=i,ent=x['entity'],others=others,hit=hit,rel=rel,nb=x['n_boxes']))
json.dump(out,open('auto.json','w'),ensure_ascii=False,indent=1)
print('with other entity named in text:',sum(1 for o in out if o['hit']))
print('with relation verb/prep:',sum(1 for o in out if o['rel']))
print('both:',sum(1 for o in out if o['rel'] and o['hit']))
print('entities having other entities in painting:',sum(1 for o in out if o['others']))
