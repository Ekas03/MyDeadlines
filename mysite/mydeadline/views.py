# views.py
import logging

from django.shortcuts import get_object_or_404, render, redirect
from django.views import generic
from .forms import DeadlineForm
from .models import Deadline

class IndexView(generic.ListView):
    template_name = "mydeadline/index.html"
    context_object_name = 'deadlines'

    def get_queryset(self):
        return Deadline.objects.all()  # Если нужно показать все дедлайны

logger = logging.getLogger(__name__)

def add_deadline(request):
    if request.method == 'POST':
        form = DeadlineForm(request.POST, request.FILES)
        if form.is_valid():
            deadline = form.save(commit=False)
            logger.info(f"Saving deadline: {deadline}")
            logger.info(f"your_name: {deadline.your_name}, your_email: {deadline.your_email}, role: {deadline.role}")
            deadline.save()
            return redirect('mydeadline:my_deadlines')
        else:
            logger.warning("Form is not valid")
            logger.warning(form.errors)
    else:
        form = DeadlineForm()
    return render(request, 'mydeadline/add_deadline.html', {'form': form})

def my_deadlines(request):
    deadlines = Deadline.objects.all()
    return render(request, 'mydeadline/my_deadlines.html', {'deadlines': deadlines})

def edit_deadline(request, pk):
    deadline = get_object_or_404(Deadline, pk=pk)
    if request.method == 'POST':
        form = DeadlineForm(request.POST, request.FILES, instance=deadline)
        if form.is_valid():
            form.save()
            return redirect('mydeadline:my_deadlines')
    else:
        form = DeadlineForm(instance=deadline)
    return render(request, 'mydeadline/edit_deadline.html', {'form': form, 'deadline': deadline})

def delete_deadline(request, pk):
    deadline = get_object_or_404(Deadline, pk=pk)
    if request.method == 'POST':
        deadline.delete()
        return redirect('mydeadline:my_deadlines')
    return render(request, 'mydeadline/delete_deadline.html', {'deadline': deadline})
