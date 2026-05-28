import json
from pathlib import Path

from django.core.management.base import BaseCommand
from parques.models import Parque, Cabana, Marcador


DATA_FILE = Path(__file__).parent / "data" / "parques.json"


class Command(BaseCommand):
    help = "Pobla la BD con parques, cabañas y marcadores leyendo parques.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Elimina los datos existentes antes de insertar",
        )

    def handle(self, *args, **options):
        if not DATA_FILE.exists():
            self.stdout.write(
                self.style.ERROR(f"No se encontró el archivo: {DATA_FILE}")
            )
            return

        with open(DATA_FILE, encoding="utf-8") as f:
            parques_data = json.load(f)

        if options["flush"]:
            Parque.objects.all().delete() 
            self.stdout.write(self.style.WARNING("Datos anteriores eliminados\n"))

        parques_creados = 0
        cabanas_creadas = 0

        for data in parques_data:
            cabanas_data = data.pop("cabanas", [])

            parque, created = Parque.objects.get_or_create(
                nombre=data["nombre"],
                defaults=data,
            )
            if created:
                parques_creados += 1

            Marcador.objects.get_or_create(
                parque=parque,
                defaults={
                    "latitud":  parque.latitud,
                    "longitud": parque.longitud,
                },
            )

            for c in cabanas_data:
                _, cab_created = Cabana.objects.get_or_create(
                    parque=parque,
                    nombre=c["nombre"],
                    defaults={"capacidad": c["capacidad"]},
                )
                if cab_created:
                    cabanas_creadas += 1

            estado = self.style.SUCCESS("creado") if created else self.style.HTTP_INFO("→ ya existe")
            self.stdout.write(f"  {estado} {parque.nombre}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n Seed completado — {parques_creados} parques y {cabanas_creadas} cabañas nuevas."
            )
        )