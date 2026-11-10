"""Hapke / Sato rough-surface model, K=1, c in [-1,1]."""
import math
DEFAULTS=dict(w=.19069647789001465,b=.26402950286865234,c=.07014839351177216,
 B_SH0=2.1867916584014893,h_SH=.07088305801153183,B_CB0=0.,h_CB=1.,theta=23.656600952148438)

def kernel(m,mu0,mu,ca,p,opposition):
    add=lambda a,b:m('ADD',a,b)
    sub=lambda a,b:m('SUBTRACT',a,b)
    mul=lambda a,b:m('MULTIPLY',a,b)
    div=lambda a,b:m('DIVIDE',a,m('MAXIMUM',b,1e-8))
    sq=lambda a:mul(a,a)
    sqrt=lambda a:m('SQRT',m('MAXIMUM',a,0))
    exp=lambda a:m('EXPONENT',m('MAXIMUM',a,-80))
    clamp=lambda a,lo,hi:m('MAXIMUM',lo,m('MINIMUM',hi,a))
    choose=lambda cond,a,b:add(mul(cond,a),mul(sub(1,cond),b))
    valid=mul(m('GREATER_THAN',mu0,1e-6),m('GREATER_THAN',mu,1e-6))
    mu0,mu=clamp(mu0,1e-6,1),clamp(mu,1e-6,1);ca=clamp(ca,-1,1)
    si,se=sqrt(sub(1,sq(mu0))),sqrt(sub(1,sq(mu)))
    cospsi=clamp(div(sub(ca,mul(mu0,mu)),mul(si,se)),-1,1)
    psi=m('ARCCOSINE',cospsi);sinhalf2=mul(.5,sub(1,cospsi))
    fpsi=exp(mul(-2,sqrt(div(sub(1,cospsi),add(1,cospsi)))))
    tangent=m('TANGENT',mul(p['theta'],math.pi/180));chi=div(1,sqrt(add(1,mul(math.pi,sq(tangent)))))
    def ef(cosine,sine):
        z=div(cosine,mul(tangent,sine));return exp(mul(-2/math.pi,z)),exp(mul(-1/math.pi,sq(z)))
    e1i,e2i=ef(mu0,si);e1e,e2e=ef(mu,se)
    eta_i=mul(chi,add(mu0,div(mul(mul(si,tangent),e2i),sub(2,e1i))))
    eta_e=mul(chi,add(mu,div(mul(mul(se,tangent),e2e),sub(2,e1e))))
    # i <= e is cos(i) >= cos(e).
    ie=sub(1,m('LESS_THAN',mu0,mu))
    d_i=sub(sub(2,e1e),mul(div(psi,math.pi),e1i));d_e=sub(sub(2,e1i),mul(div(psi,math.pi),e1e))
    ni=choose(ie,div(add(mul(cospsi,e2e),mul(sinhalf2,e2i)),d_i),div(sub(e2i,mul(sinhalf2,e2e)),d_e))
    ne=choose(ie,div(sub(e2e,mul(sinhalf2,e2i)),d_i),div(add(mul(cospsi,e2i),mul(sinhalf2,e2e)),d_e))
    u0=m('MAXIMUM',mul(chi,add(mu0,mul(mul(si,tangent),ni))),1e-8)
    u=m('MAXIMUM',mul(chi,add(mu,mul(mul(se,tangent),ne))),1e-8)
    q_i,q_e=div(mu0,eta_i),div(mu,eta_e)
    shadow=div(mul(mul(div(u,eta_e),q_i),chi),add(sub(1,fpsi),mul(mul(fpsi,chi),choose(ie,q_i,q_e))))
    phase_tan=sqrt(div(sub(1,ca),add(1,ca)))
    bsh=div(mul(opposition,p['B_SH0']),add(1,div(phase_tan,p['h_SH'])))
    x=div(phase_tan,p['h_CB'])
    cb_regular=div(add(1,div(sub(1,exp(mul(-1,x))),x)),mul(2,sq(add(1,x))))
    cb_shape=choose(m('LESS_THAN',x,.001),sub(1,mul(2.25,x)),cb_regular)
    bcb=mul(mul(opposition,p['B_CB0']),cb_shape)
    b2=sq(p['b']);t=mul(mul(2,p['b']),ca)
    backward=div(sub(1,b2),m('POWER',sub(add(1,b2),t),1.5))
    forward=div(sub(1,b2),m('POWER',add(add(1,b2),t),1.5))
    phase=add(mul(mul(.5,add(1,p['c'])),backward),mul(mul(.5,sub(1,p['c'])),forward))
    gamma=sqrt(sub(1,p['w']));r0=div(sub(1,gamma),add(1,gamma))
    def H(v):
        logarithm=m('LOGARITHM',add(1,div(1,v)),math.e)
        term=add(r0,mul(mul(.5,sub(1,mul(mul(2,r0),v))),logarithm))
        return div(1,sub(1,mul(mul(p['w'],v),term)))
    scatter=add(mul(add(1,bsh),phase),sub(mul(H(u0),H(u)),1))
    return mul(valid,mul(mul(mul(mul(div(p['w'],4),div(u0,add(u0,u))),scatter),add(1,bcb)),div(shadow,mu0)))

def scalar(op,a,b=None):
    if op=='ADD':return a+b
    if op=='SUBTRACT':return a-b
    if op=='MULTIPLY':return a*b
    if op=='DIVIDE':return a/b
    if op=='MAXIMUM':return max(a,b)
    if op=='MINIMUM':return min(a,b)
    if op=='POWER':return a**b
    if op=='SQRT':return math.sqrt(a)
    if op=='EXPONENT':return math.exp(a)
    if op=='ARCCOSINE':return math.acos(a)
    if op=='TANGENT':return math.tan(a)
    if op=='LOGARITHM':return math.log(a,b)
    if op=='GREATER_THAN':return float(a>b)
    if op=='LESS_THAN':return float(a<b)
    raise ValueError(op)

def analytic(alpha_deg,incidence_deg=30,emergence_deg=30,opposition=1,**overrides):
    return kernel(scalar,math.cos(math.radians(incidence_deg)),math.cos(math.radians(emergence_deg)),
                  math.cos(math.radians(alpha_deg)),DEFAULTS|overrides,opposition)/math.pi
