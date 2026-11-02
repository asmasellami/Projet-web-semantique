from django.shortcuts import render,redirect
from django.contrib import messages
from .multilingual.engine import answer
from .multilingual.conversation import SESSION_KEY,initial_state,submit,select,suggestions

def assistant(request):
    state=request.session.get(SESSION_KEY) or initial_state()
    if request.method=='POST':
        try:
            version=int(request.POST.get('version',state['version']))
            if version!=state['version']:
                raise ValueError('La conversation a changé. Utilisez les actions les plus récentes.')
            action=request.POST.get('action','message')
            if action=='reset':state=initial_state();state['version']=version+1
            elif action=='select':select(request.POST.get('item',''),state)
            elif action=='message':
                question=request.POST.get('q','').strip()
                if not question or len(question)>300:raise ValueError('Saisissez une question de 1 à 300 caractères.')
                submit(question,state)
            else:raise ValueError('Action inconnue.')
            request.session[SESSION_KEY]=state
        except ValueError as error:
            messages.warning(request,str(error))
        return redirect('/assistant/#latest')
    q=request.GET.get('q','')
    rep=answer(q,request.GET.get('entity','')) if 'q' in request.GET else None
    return render(request,'app/assistant.html',{'q':q,'rep':rep,'chat':state,'suggestions':suggestions(state)})
