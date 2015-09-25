"""
    urlresolver XBMC Addon
    Copyright (C) 2013 Bstrdsmkr

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Adapted for use in xbmc from:
    http://playonscripts.com/?w=files&id=34
    
    usage:

    html_with_unpacked_js = unwise_process(html_with_packed_js)


Unpacker for w.i.s.e
"""

import re

def unwise1(w):
    int1 = 0
    result = ""
    while int1 < len(w):
        result = result + chr(int(w[int1:int1 + 2], 36))
        int1 += 2
    return result

def unwise(w, i, s, e, wi, ii, si, ei):
    int1 = 0
    int2 = 0
    int3 = 0
    int4 = 0
    string1 = ""
    string2 = ""
    while True:
        if w != "":
            if int1 < wi:
                string2 = string2 + w[int1:int1+1]
            elif int1 < len(w):
                string1 = string1 + w[int1:int1+1]
            int1 += 1
        if i != "":
            if int2 < ii:
                string2 = string2 + i[int2:int2+1]
            elif int2 < len(i):
                string1 = string1 + i[int2:int2+1]
            int2 += 1
        if s != "":
            if int3 < si:
                string2 = string2 + s[int3:int3+1]
            elif int3 < len(s):
                string1 = string1 + s[int3:int3+1]
            int3 = int3 + 1
        if e != "":
            if int4 < ei:
                string2 = string2 + e[int4:int4+1]
            elif int4 < len(e):
                string1 = string1 + e[int4:int4+1]
            int4 = int4 + 1
        if len(w) + len(i) + len(s) + len(e) == len(string1) + len(string2):
            break
    int1 = 0
    int2 = 0
    result = ""
    while int1 < len(string1):
        flag = -1
        if ord(string2[int2:int2+1]) % 2:
            flag = 1
        result = result + chr(int(string1[int1:int1+2], 36) - flag)
        int2 += 1
        if int2 >= len(string2):
            int2 = 0
        int1 += 2
    return result

def unwise_process(result):
    while True:
        a = re.compile(r';?eval\s*\(\s*function\s*\(\s*w\s*,\s*i\s*,\s*s\s*,\s*e\s*\).+?[\"\']\s*\)\s*\)(?:\s*;)?').search(result)
        if not a:
            break
        a = a.group()
        tmp = re.compile(r'\}\s*\(\s*[\"\'](\w*)[\"\']\s*,\s*[\"\'](\w*)[\"\']\s*,\s*[\"\'](\w*)[\"\']\s*,\s*[\"\'](\w*)[\"\']').search(a)
        if not tmp:
            result = result.replace(a, "")
        else:
            wise = ["", "", "", ""]
            wise = tmp.groups()
            if a.find("while") == -1:
                result = result.replace(a, unwise1(wise[0]))
            else:
                c = 0
                wisestr = ["", "", "", ""]
                wiseint = [0, 0, 0, 0]
                b = re.compile(r'while(.+?)var\s*\w+\s*=\s*\w+\.join\(\s*[\"\'][\"\']\s*\)').search(a).group(1)
                for d in re.compile(r'if\s*\(\s*\w*\s*\<\s*(\d+)\)\s*\w+\.push').findall(b):
                    wisestr[c] = wise[c]
                    wiseint[c] = int(d)
                    c += 1
                result = result.replace(a, unwise(wisestr[0], wisestr[1], wisestr[2], wisestr[3], wiseint[0], wiseint[1], wiseint[2], wiseint[3]))
    return result

def resolve_var(HTML, key): #this should probably be located elsewhere
    key = re.escape(key)
    tmp1 = HTML.replace("\r", "")
    tmp1 = tmp1.replace("\n", ";")
    tmp2 = re.compile(r'[^\w\.]' + key + '\s*=\s*([^\"\']*?)[;,]').search(tmp1) #expect var first, movshare
    if tmp2:
        tmp2 = resolve_var(HTML, tmp2.group(1))
    else:
        tmp2 = re.compile(r'[^\w\.]' + key + '\s*=\s*[\"\'](.*?)[\"\']').search(tmp1)
        if tmp2:
            tmp2 = tmp2.group(1)
        else:
            key = key.split("\\.")
            if len(key) == 2:
                tmp2 = re.compile(r'[^\w\.]' + key[0] + '\s*=\s*\{.*[^\w\.]' + key[1] + '\s*\:\s*[\"\'](.*?)[\"\']').search(tmp1) #for 'vars = { key: "value" }', cloudy
            if tmp2:
                tmp2 = tmp2.group(1)
            else:
                tmp2 = "" #oops, should not happen in the variable is valid
    return tmp2

if __name__ == "__main__":
    test = "eval(function(w,i,s,e){var lIll=0;var ll1I=0;var Il1l=0;var ll1l=[];var l1lI=[];while(true){if(lIll<5)l1lI.push(w.charAt(lIll));else if(lIll<w.length)ll1l.push(w.charAt(lIll));lIll++;if(ll1I<5)l1lI.push(i.charAt(ll1I));else if(ll1I<i.length)ll1l.push(i.charAt(ll1I));ll1I++;if(Il1l<5)l1lI.push(s.charAt(Il1l));else if(Il1l<s.length)ll1l.push(s.charAt(Il1l));Il1l++;if(w.length+i.length+s.length+e.length==ll1l.length+l1lI.length+e.length)break;}var lI1l=ll1l.join('');var I1lI=l1lI.join('');ll1I=0;var l1ll=[];for(lIll=0;lIll<ll1l.length;lIll+=2){var ll11=-1;if(I1lI.charCodeAt(ll1I)%2)ll11=1;l1ll.push(String.fromCharCode(parseInt(lI1l.substr(lIll,2),36)-ll11));ll1I++;if(ll1I>=l1lI.length)ll1I=0;}return l1ll.join('');}('dd37d1u212a29333918263q01211o27312q1b3x3e1d3q01112m3q01222m3x3u37262v323p11223a251s27352116212x25211c3u2911113a251s2735211622281y11121611153x2b2q1921261u3u2v212p113w262e153x2b2q19312611121o253e1i2e2b38182x3u12111o280y12113b233x213b38182x3u12111o2e182v3b233x2b233x3b233x2b233x11113u2911222u291u2u291r2q1i27222q3e1z23141b3x111122243516212q1b3x111k1v35211d222p2e113w2o211q1g27211q1o25111s273t193126162e1e3e2b381c3y2b341x3w2u3q3u39223b3r3722291916211611121o252e1q11113w262e1d373a3x111z23141i1f1r183f1m1g1j1f1j3e181e1t3e1e1g1b3f143g1m3g1k1e1y1g121f172e1t2e102e1w2e1z2e1t2f1u2e1s1e172e1t2g1y2e1u2e152e1v3g1u2e1u1e1k2e1u1e112e1u1e1x2e1s3f1w2e1v2e1t2e1s2f172e1t2e1w2e1s2e1e2e1u2g1t2e1w2f1r2e1s3g1x2e1s2g162e1u2g1y2e1t3g1z2e1u1e1s2e1s2g1v2e1t2e1x2e1t2e1v2e1s3f1w2e1w2e1q2e1s3g1h2e1s2f1b2e1s3f102e1s2f182e1u3f1h2e1s3f172e1s3g122e1s3f172e1u3f1u2e1u3f192e1s3f1t2e1s2f192e1u3f1v2e1s3f192e1v3e1c2e1s3f182e1u3f102e1s3f192e1u3f182e1u1f192e1u3f1e2e1s3f192e1s3g1r2e1s2f192e1u3f1c2e1s3f192e1s3g1y2e1s1f172e1s3f192e1u3f172e1s3f1b2e1s2e1w2e1s1e1f1e1b2f1e3g1e1e1i1f1m3f1r3d1f3f1e3f1i2f123f1l2f1f2f1r1e1b3e1f3f1c1f1m1g1e1g1q3g1f3e1f1f1f3e1f1f161g1s1f1b1f1c3f1e3g1g3f1g2e1f1e1d3e1e1g1m3e1f1e183f133g1j2e1b1f1k3f1d1e1g3g1l3g1j3g1j3g141f1e3f1r1g1m1g1i3g1b2e1f1g1j3d1d2f1c1e1s2g1f3f1h3f123e1f3f1f1e1m3f1q3e1d3g181f1d1e123e1d1f191f1f1f1d1f1j1g1e2e1l2e1f1e1f1e1d3f1e1e181d1f1g1h1f1w2e1v3g1f2e1t2e1l2e1s2f192e1s1f1i2e1t2e1t2e1w1g1f2e1u3e1r2e1t3e1r2e1s2g1f2e1t2g1j2e1v1f1q2e1u3g1q2e1u3g162e1u2g1d2e1u2g1t2e1u2g1t2e1u2f1w2e1u1g1f2e1r2g1d2e1u1e1l2e1v2e1y2e1u3g1q2e1u2g1s2e1u1g1j2e1s3g1z2e1v2f152e1u2g1w2e1u2e1l2e1t2g1r2e1r2g182e1u3g1y2e1s1g1r2e1t1g102e1u1e1h2e1t3e1h2e1w2g1f1e1r2e1u1g152e1u2g1q2e1u3g162e1s1f1e2e1u2g1h2e1u1e1s2e1t2f1s2e1t1e1x2e1r1e122e1u1e152e1u3g152e1v2e1u2e1u2g1m2e1s1e1c2e1u1g1h2e1s1e1s2e1w1g1f2e1u1g1r2e1s1e1t2e1t3e102e1t2g142e1v1e1w2e1r1g152e1s2g1i2e1u3g152e1t3f172e1v3f1y2e1t2e1y2e1r1f1v2e1t2f1s2e1s2f1j2e1w1g1s2e1t2g1d2e1t2g1v2e1u1g1s2e1u3g181e1v2g102e1t3e1f2e1t3g1u2e1s3g152e1t1f1x2e1t2f1t2e1t1e1t2e1r1e1u2e1t2g1r2e1t2f1x2e1v2g102e1t2g1r2e1t2e182e1s2e1d2e1s1f1y2e1w1e152e1t1e1z2e1u2g1u2e1s1e1f2e1s2e1j2e1v1f1t2e1u2g1l2e1t1g1v2e1t3f1d2e1t2f1w2e1w2g1f2e1s3g162e1u1e1j2e1t1e1m2e1t2g1j2e1u2f162e1u1g102e1u1g1m2e1u3g1k2e1t2g1r2e1v1e162e1s1e162e1y2f1t3e141e141j223e161e1k3g1g2g1f3f142e1i3f1a1g1g1f1q1g1j1e123g1c1e1r3g142e1u2g1r2e1s2e1z2e1u2e1g2e1u3e1t2e1u2g1w2e1t2e1t2e1u2g1g2e1t2e1x2e1u2f1y2e1u2e182e1s2g1x2e1u2g1b2e1s1f162e1s2e1z2e1s1g1g2e1u1e1u2e1t2e1k2e1u2e162e1s2g1m2e1s1f192e1u2g1m2e1u1g1x2e1s2g1y2e1s3f102e1s2e1w2e1s1f1k2e1r2g1v2e1t3g1g2e1s1f192e1u3f182e1s3f192e1t3g162e1s3f172e1u3f1c2e1s2f172e1u3g1g2e1s3f192e1u3f1d2e1s3f182e1u3g1e2e1s3f172e1s3f172e1s2f172e1u3e1a2e1s3f182e1s3g1a2e1s3f182e1s3f1a2e1s1f172e1t3f1b2e1s3f192e1s3f152e1s2f172e1u3g1w2e1s1f172e1s3f1e2e1s3f172e1s3e1z2e1s2e1w2e1k1e123f1l1g1k1f143g121f141g1s2g1f3f143g103f1i1f1d3e1d1f161g1f1f1b1f1q3f1f3g1g3f1g3e1d1e1f1e1f1g1m3e1f1e183f133g1h2e1b1f1k3f1f1e1g2e1s1g1j3g1d3e1j3e1f1f1b3g1j1f181e122e191f1b1f1b1f1b1f1b3e181e1d3f183f153e1i1f1s3f1f1g1f3g1f1e1f3e1b3e191f1r1g1s3g123e1u1g143f1f3f171f1h1f1s2g1j2g1m1e1a3g181f1m3g1d1e1h3e1f1e1g2e1f3g1h2e1i1g1f3f1f2e163e1m2e1u3g152e1t1f1t2e1s3g1i2e1s1f1h2e1s2f1s2e1u3e1f2e1t2g1k2e1u2g1f2e1s2g1s2e1s1g1m2e1u3e1x2e1t1e142e1t1e1r2e1u2e1s2e1t1e1s2e1u2g1j2e1t2e1t2e1r2e1j2e1r2e102e1u2g1y2e1u3e1i2e1u2f1f2e1u1g1r2e1t3g1l2e1s2e1u2e1s2f1s2e1u2g1u2e1u1e1r2e1t2g1z2e1u3g1t2e1t3f1h2e1r2e1r2e1s2g1j2e1u1e1l2e1t1g1y2e1u1e153g1z2e1t2g1b2e1t2f1m2e1s2g192e1s1f1s2e1u2f152e1t2e1j2e1s1e102e1t1f1u2e1u2g1h2e1u1f1z2e1u3e1f2e1u2g142e1t2g1u2e1u1e1s2e1u3g1t2e1t3e1h2e1u2g1z2e1t1e1i2e1u1g142e1u3g1v2e1t2g1q2e1u3e1s2e1r3e1r2e1u3e182e1s1g1z2e1s3g1t2e1t1e1y2e1u2g1t2e1r1f1h2e1s2e1r2e1t3e1j2e1r1e1y2e1t3g1t2e1t2e1s2e1t2g1z2e1u2e182e1t2f1r2e1s1e1l2e1t3f102e1t3f1b2e1t1f1s2e1u2e1m2e1s1g192e1t2g1f2e1s1g1x2e1u1g1x2e1t2g1v2e1u2e1t2e1u2e1h2e1r2g182e1t2g1w2e1r2g1h2e1t2f1w2e1t2e1j2e1t2e1y2e1u3g1z2e1t1g1i2e1t2g102e1s1g1m2e1r1g1r2e1t2g1a2e1u2g1c2e1u2f162e1u2g1z2e1t2f1m2e1u2e162e1t1f1l2e1t2e1t2e1r2f1s2e1t2f1i2e1t2e1i2e1u2e102e1s2f1v2f103f161e191e2m1f1g3g1c1e1i3e1r1g1l1f1m1e1d3e1g1f1i1f1i2e1j1g1b2e152e1w1e1q2e1v2e152e1s1e1q2e1u3g1h2e1u2e1e2e1u3g1i2e1w1f1x2e1t2g1l2e1w2g1v2e1u3g1z2e1u2e1e2e1w1e1x2e1u2e1j2e1u1e1w2e1s2e1w2e1v2e122e1w2e1z2e1t2f1w2e1u1e172e1t2g1y2e1w2e172e1v3g1u2e1u2e1m2e1w1e112e1u1e1x2e1u3f1y2e1v2e1t2e1s2f192e1v3e112e1s3f182e1u3e1d2e1u3f192e1u3f1f2e1u3f1a2e1s3f1d2e1u2f192e1v3f1z2e1s1f192e1u3e1m2e1s3f172e1u3f182e1u1f192e1s3f172e1u3f1a2e1s3f1v2e1u3f1b2e1u3g1g2e1s2f1b2e1u3f1d2e1s1f172e1u3e1s2e1u3f192e1u3f1v2e1u3f1a2e1u3g1y2e1u3f192e1u3f192e1s3f192e1u2e1w2e1s2g1f1e143g1b3f1s1e1m3f1r3d1f3f1e3e1d2e1m3e1y2f1m3g1e3e1e1g1m3e1d1e1a3g153g1j2e1b2f1k1f1e1e1i2e1u1g1c3g1f1e1l3e1f1f1d3f1j3f181e142e1b3f1e1g1g3f1g2e1e3f1u1f1m3e1l1e1i1f1j1g1e2f1m3f1k1f1k3f1m3g1e3f1e3g1j1g1h3f161e1e1g1h3f1s3e1d1e1e1e1k2f141f141f1f2f1d1g1j3d1u2f1s2f1f3e1f2g163f1q1g1a1g1i3e1l1e1e1g1e3e1x1e122e1b1f1u1f1d3f1w1g1s2g1h3e1z2e1w2f1x2e1s2g1r2e1t2e172e1s1g1a2e1w3e1s2e1u3g1d2e1t1f102e1u1f1v2e1t2g1y2e1v2g1y2e1w2g1r2e1t1f112e1u2f122e1u1e1h2e1w1g1h2e1t3e102e1t1e1f2e1w1g112e1t2e1u2e1w1g1i2e1w3g1q2e1t2f102e1w2g1y2e1r3g1l2e1w2e122e1w1g1r2e1u2g1v2e1u1e1i2e1t3g1t2e1v2g1v2e1t2f1r2e1t1g1w2e1u2g1j2e1t1g1h2e1w2f1l2e1w1g1q2e153e1v1g1h2e1u1e102e1u1f1a2e1v3g1l2e1t2e1h2e1w3g1t2e1w2g192e1u2g1m2e1v3g1j2e1t1g1h2e1v1e1t2e1w3e1q2e1s3e1v2e1v2g112e1t3g1w2e1u3g1z2e1v2g1r2e1t2g1y2e1w2g1q2e1t2f1s2e1v1e1y2e1w2g1f2e1t2g1h2e1u2e172e1t3f142e1v1e102e1v3f1w2e1u2e1s2e1t2g1a2e1t2e1r2e1v3g1i2e1v3g142e1r2e1v2e1u2e1q2e1s1g1t2e1u2e1v2e1a2e1h2e1u2f1f2e1v2f1y2e1s3f1h2e1u3g1m2e1v1e162e1s2g1u2e1w1g1z2e1t3e102e1w3e1m2e1w2g1h2e1u1e1u2e1w2g162e1s2e1m2e1u2g1h2e1v2g1h2e1s2g1l2e1u1e1m2e1u2g1t2e1w3g1i2e1v2g1l2e1t1e172e1w1g1q2e1u3f1f2e1v1g1h2e1w3e1h2e1r2f1u2e1v2g1z2e1t2g1m2e1v2e1j2e1v1g1r2e1t3g1v2e1u1g1t2e1t2f1f2e1u3e1s2e1v2g152e1t2e183e112e1x2f173e192s2s1t2l1l1q2h1h2t2t2m16','57e51m3o1v3s221a271u3b3v2z1b3q01101m25212q193v3c1k1b3v1z1i1c21173s3w1121141z133x3b2o1730261u3s2t302p113u243c153x392o1722261z3z1m252e1g3c29381y2v3s1z121o360w1z122b213v3z2b381w2v3s11121m3c162v213n1z303a251q25332e162z2v232e183s271z113a231q25352e142z361y1c3s271w2u29163s271u2u271o3c113w261z1z3w281z3u243u2o3o0z1z212b3w121m272e2o1z1x23141z101m272e3o2m35222q1z3z3z2b233v3036163q0z1c1c2v2e292o122u11101d3z1q113z3823373w253u253t1536211z113a371z3z161j1z1c1m2e182t3z2p2e2b213v3z2q1i27313c2b3y121m121l1e1d1d1c1e1h1c102d1m1e1a2e1k1e1a3e161e171g1i1c1i1f1f2c1q1d1t2e1r2e1r2e1s3c1u2c1u2g1c2c1s1e1z2c1q3c1t2e1s2c122e1s2e1k2c1w1e1i2c1s3e1h2c1s2d112e1q3c1x2e1t1d1s2c1u1f1s2c1q2e1u2c1r3e1x2e1s2c1t2e1u3e172c1w1f1w2c1r2g1q2c1q2d102e1r2e1j2e1t1c1s2c1v2e1q2c1q2e1y2c1q3c1b2e1s2e1y2e1s3c152c1v3g1r2c1q2f172c1q3d1z2e1q3d152e1s3d1c2c1u2f172c1q3f1a2c1q1d1b2e1r3e142e1s3d162c1u3f1t2c1q1f172c1r3d1e2e1q3d162e1s3d122c1u3f172c1s3f1a2c1q3d1a2e1q3d1f2e1s1d172c1u3f1b2c1q3f172c1q3d1v2e1q2d172e1s3d142c1u3f152c1r3e1i2c1q2d192e1q3d172e1s3d152c1w2e1s2c1q2e1e1c1d1c1r1g1a1c1i2f1d3c192c161e101d123f1s3d1a1e1w1f1u2d1h2f181d101b1e3g1c3d1k1e1b3c1d3d1l3f113d1j1e1i1d1f3d1i2e161c1d1f161e1q1d1l3e1d1c1e3g141d1f3e1b3f1d3d1q1g1m3c1d1c1e3f1d3d1d3f1f3d1d3d1e1f192d1c3f1e3d1c1e1u3e1d1c121f1s2e1d3d1t3d1d3d1d3e1f1c161c1e2g192c1a1f1b3d1e2c1e2e1d1e1i1e1d3c1e1d1i2e1h1d1r2e1s1d1h3c1f3f161c1b3g1i1d1d1c1i3f1r2e162e1t1d1p2c1u1g1y2c1q3g1f2c1q1e1z2e1q3c1h2e1u2e122c1w2g142c1q3g1t2c1r2c1v2e1q2e1f2e1u1c132c1v3f122c1r2g1u2c1s2e1s2e1r2e1s2e1u1e1q2c1v3g1h2c1s2g1s2c1r2c1f2e1q1c1p2e1t2e162c1w2g1r2c1s2g1g2c1q2e122e1p2c1p2e1t2c1q2c1w2e1w2c1p3e1t2c1q1c1r2e1r2e142e1u1e1f2c1w1g1d2c1r2g1d2c1s2e182e1r1c1o2e1f3d1s1c1h2e1s1d1x2e1s3e1c2c1u3f1g2c1r2e1w2c1s3d1k2e1r1e1o2e1t1c1j2c1w3e1i2c1s1g1k2c1p1c122e1q1e1x2e1r2d1t2c1w3e1k2c1r2e1m2c1r2e1f2e1r2e1f2e1s2c1j2c1v3g1d2c1p2f1a2c1r2c1y2e1s1e1f2e1t2c1i2c1v2g1r2c1q2f142c1q1c102e1s2c152e1t1c1x2c1u2g1k2c1r2g1r2c1r2e1v2e1q2e1j2e1t1c1q2c1u2g1t2c1s1e1k2c1r1c122e1d2d1y2e1u2e122c1v2g182c1q2e1b2c1r1d1m2e1s2c1s2e1t2e1d2c1w2f1d2c1s1g1z2c1r3c1y2e1r3c1p2e1t1c1y2c1u2e1p2c1s1g1t2c1s2d1j2e1r1c1j2e1u2e1f2c1w2e1y2c1r2g1h2c1s2c1t2e1q2c1g2e1r3e1q2c1w1e1h2c1r2g182c1r2c1v2e1s2d1w2e1r2d122c1v3f1d2c1q2e1g2c1r2e1v2e1p2d1r2e1s2e1e2c1v3g1d2c1r2g142c1q1e1w2e1s2e1f2e1t2c1d3c1v3e1p3c153f1h171d2t143g1d2d163g1r3c183c1u3g181e1g3e1j1c1j1c1h2e161b1e3f142c1s2e1t2e1s2d1p2e1s3e1v2c1s2g122c1s2g1y2c1r2e1z2e1q1c1q2e1s2e1t2c1t2e1t2c1r2e1v2c1q3d1w2e1s3c1o2e1s3e1f2c1s2e1x2c1q2e1e2c1q1c1i2e1q3c1x2e1u1c1t2c1u1f1p2c1r1e1g2c1q1d1x2e1r2c1k2e1u1e1t2c1t2e132c1s2e1y2c1q3c1e2e1s2c1p2e1s1d142c1u3e1e2c1q3f192c1s3e162e1q3d152e1s3d1c2c1s1f172c1q3f1v2c1q3d192e1q3c162e1s3d172c1u3g192c1q3f182c1q3d182e1q3d172e1u3d1t2c1s3f162c1q3e1c2c1q3d192e1r3e1b2e1s3d172c1s3g1i2c1q1f172c1s3e1c2e1q3d172e1u3c1o2c1s1f152c1r3e1i2c1q3d172e1q3d1c2e1s3d152c1s2e1x2c1q1e1k1c163d1k1g1h1e1d3e1i3d1k3e1r3d1d3e1d1f1b3e1f3e133g1j1c1g1f1h3d1e3c181e1d1d141g1f1e1h3c1d1e1e3d121f1h3e173d1f3f1q1e1k3e1f1c1b3d1s2g1k1c193e1f3e1a1c1m1g1d1e1h3g1d3c1q1d1m1g1k1e1k1g1m1e1d3e1k3g161c161e142d1b3e1d1e1k3c1d1f1g1e121e1f2e1e3c1b3f1f3d1d3c1i3e101c141g1k3d1f2c1s1g1o3d1d3g183e1i1e151g1i1c1d1e1d3d1q3c1f3f1q2e1j3e1d1c1u3c102e1q1c132e1u2e1d2c1s3f172c1r3f1h2c1s2e1y2e1r1e132e1t2c1r2c1t2g1u2c1r1e1t2c1r1c1f2e1q3c1a2e1u1c1d2c1u1e1h2c1p1g1w2c1r2e1g2e1q1c1x2e1t3e1v2c1t2e1u2c1r1e1w2c1s2e1q2e1s2e132e1t2c1w2c1t1e1i2c1s1g182c1s1c1r2e1q3e1x2e1u1e1r2c1u2g1b2c1p1e1t2c1r2e162e1r1e122e1t1c1o2c1u1g1w2c1q2g1j2c1q2e1f2e1s1e1d1f102c1s1e1z2e1r1c1y2e1s1d1x2c1s3g1e2c1r1g1y2c1r3e1r2e1r3d1k2e1u2e1d2c1s2g1w2c1q2g1i2c1s1e192e1s2e1p2e1u2c1u2c1u2e1d2c1p1e102c1p2c162e1p1e1r2e1u1c1d2c1u2g1d2c1s2g102c1r1c1z2e1r2e122e1t2e122c1t1f122c1s1f1k2c1p3c102e1q3c1k2e1u3e1t2c1u3f1k2c1r3g1t2c1p3e142e1s1d1i2e1u1c132c1r1g1p2c1s1e1u2c1q2e1v1f1p2e1v2e1s2e1d2c1s1e1b2c1q1g172c1r3e1f2e1s3d1o2e1u3c1h2c1t2e1p2c1s1e1f2c1s3e1d2e1q1e1v2e1s2c1u2c1s2f1s2c1r2g1y2c1s3e1r2e1r2e1p2e1u2e1p2c1u2g1w2c1s2e1y2c1s3e182e1r3e1h2e1s1d1r2c1u1g1i2c1r3g1m2c1r3e1t2e1p1e1p2e1u1e1w2c1t2e1r2c1q2g1s2c1r2e1r2e1q3e1k2e1s1e1u2c1t1g1u2c1s2f1t2c1r2e1y2e1r2d1y2e1s1d1r2c1u3e122d1d341l1p1k1e1c1e1k2e141g1g3e1f1d1e3g141d1i1g1l1e1r2c1i2g1w2c1r1g1i2c1s1c1u2e1t3c1k2e1w2c142c1s2g1p2c1s1f1b2c1s2e1m2e1u2e1x2e1u2e1w2c1s3f102c1s2e1y2c1q1d1k2e1r2e1v2e1v3e1e2c1s2e1u2c1s1f1t2c1r3e1t2e1s3c1w2e1u2e1c2c1u1e1z2c1s3e1t2c1s2c142e1s2e1p2e1w1c1i2c1u3e1h2c1u2f112c1q3c1z2e1t1d1u2e1u1d152c1t3e162c1s3f1a2c1s3d182e1s1d172e1u3c192c1s3f172c1u3g1v2c1q1d192e1s3d1b2e1u3d152c1s3g162c1s1f1b2c1q3d1g2e1s3d172e1w3d122c1s2f192c1s3f112c1q1d192e1s3e1w2e1u3d172c1t3f1b2c1s3f192c1q3c1e2e1s3d182e1v3d172c1s1f172c1t3e1b2c1q3d172e1s3d192e1u2c1s2c1s2e1w1c1f1e143c141c1k3g1b1c143e141d122e1s2e1b1c1q3e1a3c1d1c1g3g141e1h3g1b1d1d3d1s1g1p3c1d1e1e3d1q2d1m1e1b3c1d3f1e3c1k1e1f2g1c3e1c1e1u1d1d3c1d2f161e1s1f1d1d1h3d1f1g1g3d1g2e1e1c1o3d1c3f1j3d183f162c181c1f3f1c3d183g1e3d1k3c121f141c1e1e1f3d1q3d1i1f1c1e1p1g1f1c121c1s3f1p3c183e1v3c1d1e1g1g1i3d171g1g3c1j1c1f1e1c2c1s1f1e3d1k1e1f3e1k1e1p3e141d1p2e1y2e1u1e1t2e1w3e1p2c1s1f1g2c1t3g122c1s3d152e1t2e1g2e1v2c1h2c1t1f1r2c1u1g1t2c1r2e1y2e1s2e1f2e1w3d1y2c1u2e1f2c1t2e1h2c1q2c172e1u2e1f2e1w2d1f2c1t2e1y2c1t2g1h2c1q2e182e1u2e1y2e1w3e1o2c1u2e142c1t2g1u2c1r2e1l2e1s3c1w2e1v2c1d2c1s2f162c1r1g1v2c1r2c1s2e1s3e1h2e1v2e1v2c1u2e1d2c1u2e1u2c1s2e1l2e1s1d141g1j2c1s2e1m2e1t3c1f2e1u1d132c1s3g1p2c1t3f182c1s2e1t2e1s3e1t2e1w3d132c1u2g1j2c1t3g1j2c1r2e152e1u2c142e1w2d1y2c1u2e162c1u1e192c1s2c1z2e1t1c1x2e1w2d1p2c1u1e1x2c1u1g1j2c1r1e1v2e1t3e1r2e1v2c1v2c1t2e142c1u2g1l2c1p1c102e1s3e1w2e1w2c1r2c1t3e1p2c1r2g1a2c1q2c152e1t3e1q2e1v1e1w2c1u2g1j2c1u1g1u2c1q1c1r2e1u3c1w2e1v3c1p2c1r3e1d2c1t3g1f2c1s3c1m2e1u2e1x2e1v1e1d2c1t1g152c1r1e112c1p1d1q2e1u2e1j2e1v2c1s2c1s3g1w2c1t1e1w2c1q2e1x2e1s1c1t2e1u3c1f2c1t2e1w2c1u2e122c1q1c1x2e1u1c1j2e1v1e1g2c1t1e162c1u2e1k2c1s2c142e1t1e1r2e1w3d1y2c1t1e1z2c1s3g1v2c1r2c1m2e1u3c102e1v2d1j2c1u3g1o2c1s3g112c1s2e1x2e1t2e1t1f183d1x3d1v3f10121p1s1f1s1i1b2u1d2r1r2o161','18da52b33313y351y371e27323q193v3e1d3q001z1o27313o2m273e2q2m2w253a1g232z1i3e2b361a2x3u113z1m380y113z39233x3139361c2x3u1z3z1o21182t3z2p113238231s27353c14212x253c1w3u29111z38251s27333c1631281w10111611133v3b2q192z341u3u2v2z3n113w263c133x3b2q172z3612111m23113w281z3u28113w261z3w2q3139213x3e2b213v2b233x252y3b3x2e1z1z2435163o00323e2b3w121o3e1d3o0z312m241z3z1o21111z3s2911311d393x3e1a1w10322x3w2s333e12111c1m11153x27211v322q12232722352c162835211d1e1a3e163z261y11121z303u2911101m3u37013z223516351j2j3f1l1g1i1d1h1e1q3d1h2g1q3f1d3e1a3g1k1e1g1e1h2f1c3c1u3f1k2c1r3e1z2e1s2e102e1t2c1w2e1s3f1i2c1u2e182c1q3e1r2e1s2c1s2e1t1c1e2e1u3e122c1w2e1z2c1q2e1b2e1s2e1g2e1t3e1h2e1s2e1s2c1u1g142c1s2g1r2e1q2c112e1u2c1e2e1u3e1r2c1w2g1w2c1r2e1t2e1s2e1i2e1t2c1v2e1u2f1w2c1w2e182c1q2g1x2e1s2e1d2e1s1d142e1u3g1t2c1u3f192c1q3f192e1q1d1a2e1s3d1x2e1s3f172c1u3e1i2c1q2f172e1s3d162e1s2d152e1t3f1j2c1u2f192c1s3f142e1q3d1b2e1u3c1a2e1s3f152c1w3f1d2c1q3f172e1r3d1e2e1s3d152e1s3g192c1u2f172c1r3f1z2e1q3d182e1u3e182e1s2f162c1w3g1v2c1q3f172e1q3d1b2e1s3d1s2e1s2e1s2c1h1e1h3d1e1g1g3g1s1d161g1s2e1b3e1i1f101d163f1g1c1e3e1s2g1o3e1e3e1j3c1d1f1b1f1h2d1a3f123c173f1f1g1e3d1i2e1f3d1q3f1k1e1j1c1k1f1h3d1a1e1h1e191d1m3f183d1d3e1a1f1e3e161f1h1c101e1a1e181c1c1e1a3d1k1g1s2f191d1d1f1m3d1d3f1g1g1b1d1r3e122c123f101e1d3d1e3f1k3d1r1g1s2e1b1d1c3g1s1c1q3e1g3f1c3e161f1i1e1q1f1g1e1s1d1j3f1c3c1d1f1k1e103e1e3f1g1e172e1t2e1r1d1h2e1s1e1d2e1s3f1a2c1v1g1d2c1r2e142e1p1d1s2e1s2e1u2e1t2e162c1v1e1r2c1r1g1t2e1p2d1m2e1t2e1d2e1u3g1u2c1w1e1z2c1s2g1w2e1s2c1h2e1r2c122e1u1e1r2c1v1e1q2c1r1g1i2e1s2d1t2e1t2c1o2e1t2g1w2c1u1f1t2c1q2g1q2e1q3c1z2e1u2e1u2e1t1g162c1u2g1m2c1p3f1y2e1r2d1i2e1t2e1h2e1u3e1s2c1v1g1y2c1s1g1j2e1r1e172e1k2c1s3e1m2e1s2c122e1s3c162e1t3g1r2c1w1e142c1r2g1k2e1r2e1h2e1s2e132e1u3e1f2c1w3g1k2c1q3f1d2e1s2c1w2e1t1c132e1u3g1v2c1u1e1t2c1s2f1y2e1s1c1v2e1u2e142e1u2g1w2c1w3e1q2c1s3e1f2e1q2d1v2e1u3d1y2e1u1f1u2c1w3g1i2c1p3e1w2e1r2e1h2e1u2c1q2e1t2g1s2c1w2g1q2c1s1f1t2e1r2e1j2e1t1d1o2e1r2e1j2c1t2e1d2c1r3e1t2e1r3c1u2e1s1e1v2e1t2f1y2c1u3f1k2c1q2g1t2e1s2e1t2e1t2e1q2e1u2e1b2c1v2g102c1p2g152e1r3c1j2e1t2c1p2e1s3e1h2c1w1e1r2c1s2g1f2e1s3e1v2e1t2e1v2e1u2e1w2c1w1e1w2c1r1f1y2e1r2e122e1r1e1b2e1t2g1y2c1w1g1y2c1r2e1v2e1r1e1v2e1u3c142e1u1e1u2c1u1e1t2c1p1e1s2e1s3e1x2e1t3c122e1t1e1r2c1w1g1m2c1s2e1t2e1r3c1u2e153c162e182f153c141h1q3e173f1q1e171c133g123c121g1i3f151e1e2g1k1c1v3g1i3g132c1t3g1v2c1s2e1v2e1s2e192e1u1d1w2e1t2g1o2c1s2f1y2c1r2g1l2e1r1c1u2e1t2c1q2e1s2e1w2c1s3e192c1s2g102e1q3c172e1t3e1x2e1s2e1u2c1u1e1l2c1r2e152e1q1c1l2e1s3e1d2e1u1e1c2c1s3g1g2c1s1f1x2e1r2e1j2e1u2e1r2e1u3g1x2c1s2e1c2c1s1e1x2e1s2c1h2e1s1d162e1u3f182c1s3f192c1q3f1a2e1q3d192e1u3d1j2e1s3f172c1t3e1d2c1q1f182e1s3e152e1s3d152e1t3f1b2c1s3f182c1s3g102e1q3d182e1s3d172e1s3f162c1s3e172c1q3f172e1q3c1d2e1s3d152e1s3g1j2c1s3f192c1s3f1f2e1q3d172e1s3d1h2e1s2f162c1u3f1e2c1q3f172e1q3d1b2e1s2c1x2e1s2e1i1c1h3e1f1d1c1e1h3d1d3d1f3e1b2c123e103d1b3e181f191d1d1g1g3f1e3c1f3f1f2d1i3e1l1e1g1d1h1g1c3c1f3e1b1f1i3d183f1f3c181f1g3f121e1h3e121d1u2f1j1f161c121d1d3e1c3f1m1e193c1f3g1j3e1c3f1e3g1c3d1e3e1f3d1d1f1k3g1i3d1w1g142c1c1e1b3e1b1e1h3f1m3c1w3g1f2g112c1a3f142d1d3e1g3e1g3c1f1e1s2d1k1e1c1g193d143g1d1e1g1f1k1g1f3c121g143c181f1r1g193c1e1e173c1r1e1k2e1r3e1w2e1u2e1d2e1s1g162c1r1e1t2c1s2f1h2e1r1e1s2e1t1e1q2e1u1g1k2c1s2g1m2c1r1e182e1q2e1j2e1u3c1i2e1s2g1d2c1u2g1r2c1s2f1f2e1s1e162e1u2e1r2e1u1e1d2c1u3g1y2c1r2f1y2e1q1c1r2e1t1e1d2e1u2f1f2c1u1e1j2c1r2g152e1s2c1k2e1t2e1y2e1u2f1k2c1u2g1t2c1r2e1m2e1s1e1l2e1t2c1g2e1t1g1u2c1t1e1u2c1q2g1g2e1d3d1r2g1d2c1s3g1f2e1q1e1d2e1t3d162e1s2g1g2c1s3f102c1q1e182e1s3e1s2e1t2d1x2e1u1g1v2c1s2g1i2c1p1f1w2e1s3d1s2e1u2c1w2e1s2f1k2c1u2f1w2c1s1e1f2e1r2c1h2e1s1e1u2e1u3e1w2c1u2g1f2c1r2e1w2e1r2c1t2e1t2c1j2e1s3f1g2c1t2g1b2c1r2e142e1s2c102e1s2e162e1t1g142c1u2f162c1r1f1j2e1r2e1e2e1t2c1f2e1t2g1g2c1s2e1q2c1d3e1r2e1r2c1y2e1u1e1b2e1s3f1h2c1s3f182c1s2g162e1r1c102e1u3e1y2e1u1f1g2c1t2e182c1r2g1f2e1q2e1r2e1t2c1w2e1t1e1p2c1t3e152c1p2e1s2e1r1c1u2e1u2e1r2e1r1e1y2c1t2e102c1s2e152e1s1e1j2e1r3e1d2e1s1f122c1t2g162c1r3f1l2e1q3e1j2e1t3c1y2e1u2e1x2c1r1g1s2c1r3g162e1p1c1k2e1s2e1d2e1t2g1o2c1u1e1q2c1q1e1x2e1r3c1f2f1x2c153e1u3e10121g1f1i1e1g3g1w1g1h2d1b1e1l1d191f1h1f1b1c1j1e1w1e1o3e1u3f1c2c1s2e1k2c1s3e112e1s2c1v2e1w1d1r2e1v1e1e2c1s1f1z2c1t2e1r2e1s1e1v2e1v2c152e1w2e1w2c1s3e1g2c1u2e1t2e1q1d162e1u2c1u2e1u2g1i2c1t3e112c1u2g102e1r2c1y2e1u3d1k2e1u2e162c1s3e1t2c1u2e1s2e1r1c1g2e1w3c142e1w2e1x2c1s2e1d2c1u2g1g2e1r3e1j2e1u3d182e1u3e1d2c1s1f1b2c1s3g1d2e1q3d182e1v3c192e1u3f152c1s3e1j2c1s2f1a2e1s3c1d2e1u1d192e1u3e1f2c1s3f1a2c1u3f1b2e1q3d192e1u3c1z2e1u2f172c1s3f1d2c1s1f1b2e1q3d1c2e1u1d172e1v3g192c1s2f1a2c1s3f1a2e1q2d172e1v3c1j2e1u2f162c1s3f1b2c1s3f192e1q3d1t2e1u2c1u2e1h1e1d3b143g1h2d181g1e2g1d1c1i1f1r3e1y1g1e2e1d1e1c1f1j1c1b1f1m1f163d1d3e1c1e1g3g161f1f1d121f1y2d1j3f1a3e101b1f1f1g3e1p1e1d3e1b3d1j3f151e1o1e1k1f1f1d1g2e1a1c1c1f181g1q1d1j3e1a1c181e1a1e161c1s1g1l1c1a1e1c1g103b1f1f1e1c1i2f1e3f1d1c121f163e1d3e1e3f1c3d1j1g1e2c192f161f1d1c1f3e1e2d1i3f1c1g1e1d1f1g1m1e1h2e1u3f1h3d152f1g3e142f1g2f1a1c1f2e1y2c1s2g1k2e1r2e172e1u3d1i2e1u3g142c1t2g162c1s1g1z2e1q3e1r2e1w2e1f2e1w2g1d2c1u2g1t2c1t2g1v2e1s3e102e1v3d1z2e1w1g1v2c1t1e1v2c1u3g1s2e1r1c1s2e1u3e1x2e1w2g1w2c1u1g1t2c1t2e1t2e1s3e152e1t2e1t2e1v1g1p2c1t3e1t2c1s2f192e1s2c1r2e1w1e1z2e1u2e1k2c1s2f1r2c1s2e162e1r2c1w2e1u1c1t2e1v1g1y2c1t1g1t2c1t2g1m3e1d2c1u1f1s2c1u3g192e1q3d1d2e1u1d1a2e1u1g1d2c1u2e1y2c1t3g112e1q1c152e1v1c1t2e1v1f142c1t2f1z2c1u2e1t2e1s2e1s2e1v3d1r2e1v2g1f2c1t2e1y2c1u2g1j2e1s2e1t2e1w2e1f2e1v2e1d2c1s2f1h2c1t1e112e1r1d1y2e1v3e1u2e1v3f1p2c1s3f1m2c1t2e112e1r2c1s2e1u3e162e1w2e1p2c1s1g1z2c1u3g112e1s2e1h2e1w2c1y2e1v2g1h2c1u2f1m3c1u1e1c2e1r1e102e1u2c162e1v1f152c1s1e172c1s3e1v2e1s2e1k2e1v2e1f2e1v3g1f2c1t1e1j2c1r1e1s2e1s2e1u2e1w3d102e1w1g1f2c1u1e1s2c1u1f1h2e1r1c142e1w1c1s2e1w2g1x2c1u1g1j2c1r1g1f2e1s3e1j2e1u2e1j2e1v1g1r2c1r1e1u2c1u1g1d2e1r2d142e1v2e1f2e1u1g162c1r1g1u2c1r2f182e1s2c1y2e1w2e162e1v3g132c1s2e1v2c1r3f1z2e1i3d173e162c173f1j142c2d2j1h1g2r1k1q2g2s121m','bc1cc22d6e847830ade4904add3ddca9'));"
