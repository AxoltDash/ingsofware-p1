from django.db import models

# Create your models here.
class Zapato(models.Model):

    agujeta = models.CharField(max_length=100)
    color = models.CharField(max_length=100)

class Escuela(models.Model):
    nombre = models.CharField(max_length=100)
    clave = models.CharField(max_length=15)
    nivel_educativo = models.CharField(max_length=50)
