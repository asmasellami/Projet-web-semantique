from django.shortcuts import render
from .multilingual.contracts import CONTRACTS
from .multilingual.engine import answer

def assistant(request):
    q=request.GET.get('q','')
    rep=answer(q,request.GET.get('entity','')) if 'q' in request.GET else None
    return render(request,'app/assistant.html',{'q':q,'rep':rep,'contracts':CONTRACTS.values()})
