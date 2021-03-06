from django.db import models
from django.conf import settings
from django.utils import timezone
from simplemooc.core.mail import send_mail_template

class CourseManager(models.Manager):
    
    def search(self, query):
        return self.get_queryset().filter(
            models.Q(name__icontains=query) | \
            models.Q(description__icontains=query)
        )

class Course(models.Model):
    
    name = models.CharField('Nome', max_length=100)
    slug = models.SlugField('Atalho')
    description = models.TextField('Descricao Simples', blank=True)
    about = models.TextField('Sobre o Curso', blank=True)
    start_date = models.DateField('Data de Inicio', null=True, blank=True)
    image = models.ImageField(upload_to='courses/images', verbose_name='Imagem', null=True, blank=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    objects=CourseManager()
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('courses:details', args=[self.slug])
    
    def release_lessons(self):
        today = timezone.now().date()
        return self.lessons.filter(release_date__gte=today)
    
    class Meta:
        verbose_name='Curso'
        verbose_name_plural='Cursos'
        ordering=['name']
        
class Lesson(models.Model):
    
    name = models.CharField('Nome', max_length=100)
    description = models.TextField('Descricao', blank=True)
    number = models.IntegerField('Numero (ordem)', blank=True, default=0)
    release_date = models.DateField('Data de liberacao', blank=True, null=True)
    course = models.ForeignKey(Course, verbose_name='Curso', on_delete=models.CASCADE, related_name='lessons')
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    def __str__(self):
        return self.name
    
    def is_available(self):
        if self.release_date:
            today = timezone.now().date()
            return self.release_date >= today
        return False
    
    class Meta:
        verbose_name = 'Aula'
        verbose_name_plural = 'Aulas'
        ordering = ['number']
        
class Material(models.Model):
    
    name = models.CharField('Nome', max_length=100)
    embedded = models.TextField('Video embedded', blank=True)
    file = models.FileField(upload_to='lessons/materials', blank=True, null=True)
    lesson = models.ForeignKey(Lesson, verbose_name = 'Aula', on_delete=models.CASCADE, related_name='materials')
    
    def is_embedded(self):
        return bool(self.embedded)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiais'
        

class Enrollment(models.Model):
    
    STATUS_CHOICES = (
        (0, 'Pendente'),
        (1, 'Aprovado'),
        (2, 'Cancelado'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Usuario',
        on_delete=models.CASCADE, related_name='enrollments'
    )
    course = models.ForeignKey(
        Course, verbose_name='Curso', on_delete=models.CASCADE, related_name='enrollments'
    )
    status = models.IntegerField(
        'Situacao', choices=STATUS_CHOICES, default=1, blank=True
    )
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    def active(self):
        self.status = 1
        self.save()
        
    def is_approved(self):
        return self.status == 1
    
    class Meta:
        verbose_name = 'Inscricao'
        verbose_name_plural = 'Inscricoes'
        unique_together = (('user', 'course'),)

class Announcement(models.Model):
    
    course = models.ForeignKey(
        Course, verbose_name='Curso', on_delete=models.CASCADE, related_name='announcements'
    )
    title = models.CharField('Titulo', max_length=100)
    content = models.TextField('Conteudo')
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'Anuncio'
        verbose_name_plural = 'Anuncios'
        ordering = ['-created_at']
        
class Comment(models.Model):
    
    announcement = models.ForeignKey(
        Announcement, verbose_name='Anuncio', on_delete=models.CASCADE, related_name='comments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='usuario', on_delete=models.CASCADE
    )
    comment = models.TextField('Comentario')
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering = ['created_at']
        
def post_save_announcement(instance, created, **kwargs):
    if created:
        subject = instance.title
        context = {
         'announcement': instance   
        }
        template_name = 'courses/announcement_mail.html'
        enrollments = Enrollment.objects.filter(
            course = instance.course,
            status = 1
        )
        for enrollment in enrollments:
            recipient_list = [enrollment.user.email]
            send_mail_template(subject, template_name, context, recipient_list)
        
models.signals.post_save.connect(
    post_save_announcement, sender=Announcement, dispatch_uid='post_save_announcement'
)
