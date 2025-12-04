"""
Seed Data - Poblar base de datos con datos de ejemplo

Este script crea datos de ejemplo para el demo de mock_ai Agent.
Se crea UN SOLO cliente con 2 sucursales para simular un escenario realista.

INSTRUCCIONES:
1. Edita la sección CONFIGURACIÓN DE CALENDARIOS abajo
2. Reemplaza los google_calendar_id con los IDs reales de tus calendarios
3. Ejecuta: python -m src.db.seed

Ejecutar: python -m src.db.seed
"""

import uuid
from datetime import datetime, time
from decimal import Decimal
from .database import get_db


# =============================================================================
# CONFIGURACIÓN DE CALENDARIOS - EDITA AQUÍ LOS IDs DE GOOGLE CALENDAR
# =============================================================================
#
# Para obtener el Calendar ID de cada calendario:
# 1. Ve a Google Calendar (calendar.google.com)
# 2. Click en ⋮ junto al calendario → Settings and sharing
# 3. Baja hasta "Integrate calendar" → Copia el "Calendar ID"
# 4. Reemplaza el valor correspondiente abajo
#
# El formato típico es: abc123xyz@group.calendar.google.com
# Si usas el calendario principal de una cuenta: email@gmail.com
#
# =============================================================================

CALENDARIOS = {
    # -------------------------------------------------------------------------
    # SUCURSAL 1: CLÍNICA CENTRO
    # -------------------------------------------------------------------------
    # Medicina General
    "mario_gomez": {
        "nombre": "Dr. Mario Gómez",
        "google_calendar_id": "c_4d568dba17af0b4b1475419e0ed91f16e862b1d8b663c834103fe71dce014bf6@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "mario.gomez@clinicassaludtotal.com",
        "horario_inicio": time(8, 0),  # 8:00 AM
        "horario_fin": time(16, 0),  # 4:00 PM
    },
    "laura_rodriguez": {
        "nombre": "Dra. Laura Rodríguez",
        "google_calendar_id": "c_b9475fb3be7f0e40c82b5ced35d7d0b9a7d736144a4afb4cb157f3c63556853e@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "laura.rodriguez@clinicassaludtotal.com",
        "horario_inicio": time(10, 0),  # 10:00 AM
        "horario_fin": time(18, 0),  # 6:00 PM
    },
    # Pediatría
    "susana_torres": {
        "nombre": "Dra. Susana Torres",
        "google_calendar_id": "c_d07558457d0464f440f775002dcb266bd5cb5712258661db5a8505a1b1eb892a@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "susana.torres@clinicassaludtotal.com",
        "horario_inicio": time(8, 0),  # 8:00 AM
        "horario_fin": time(14, 0),  # 2:00 PM
    },
    "pedro_morales": {
        "nombre": "Dr. Pedro Morales",
        "google_calendar_id": "c_47f2f2ebc425d5cbdbb3b934dc4969ca7359593c2fedd3353dbca6653a4beb3b@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "pedro.morales@clinicassaludtotal.com",
        "horario_inicio": time(14, 0),  # 2:00 PM
        "horario_fin": time(19, 0),  # 7:00 PM
    },
    # Cardiología
    "roberto_vega": {
        "nombre": "Dr. Roberto Vega",
        "google_calendar_id": "c_403619db14549777524cdee20d1359b8b228c54d98cfd8ae9f9f948453323079@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "roberto.vega@clinicassaludtotal.com",
        "horario_inicio": time(9, 0),  # 9:00 AM
        "horario_fin": time(17, 0),  # 5:00 PM
    },
    "carmen_diaz": {
        "nombre": "Dra. Carmen Díaz",
        "google_calendar_id": "c_cb80ed4dcbc060e1c1cf6f9939f154b995bbc38cf6290d62bf1bbe91baf5d5c6@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "carmen.diaz@clinicassaludtotal.com",
        "horario_inicio": time(11, 0),  # 11:00 AM
        "horario_fin": time(18, 0),  # 6:00 PM
    },
    # -------------------------------------------------------------------------
    # SUCURSAL 2: CLÍNICA NORTE
    # -------------------------------------------------------------------------
    # Odontología
    "maria_lopez": {
        "nombre": "Dra. María López",
        "google_calendar_id": "c_f91d06eb7979620612e545cd08cccb2053757376c933c52c99ab233cd144631b@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "maria.lopez@clinicassaludtotal.com",
        "horario_inicio": time(9, 0),  # 9:00 AM
        "horario_fin": time(17, 0),  # 5:00 PM
    },
    "carlos_andrade": {
        "nombre": "Dr. Carlos Andrade",
        "google_calendar_id": "c_a12318900504bda739bc8cab72da9784d10446c9a16cb32b20f51b7a6b864d90@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "carlos.andrade@clinicassaludtotal.com",
        "horario_inicio": time(12, 0),  # 12:00 PM
        "horario_fin": time(18, 0),  # 6:00 PM
    },
    "felipe_herrera": {
        "nombre": "Dr. Felipe Herrera",
        "google_calendar_id": "c_c332bac9f6797e7d0792fe2703620323241f93db16c6e1110243b6c806f08df8@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "felipe.herrera@clinicassaludtotal.com",
        "horario_inicio": time(9, 0),  # 9:00 AM
        "horario_fin": time(14, 0),  # 2:00 PM
    },
    # Dermatología
    "ana_martinez": {
        "nombre": "Dra. Ana Martínez",
        "google_calendar_id": "c_cbdab804073fb2f44bc1482ef2a1230d37049b12756a56994eaedafd60859522@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "ana.martinez@clinicassaludtotal.com",
        "horario_inicio": time(9, 0),  # 9:00 AM
        "horario_fin": time(16, 0),  # 4:00 PM
    },
    "javier_paredes": {
        "nombre": "Dr. Javier Paredes",
        "google_calendar_id": "c_0716da018b8a25e6635c8deb52711f5082c087c546c831eb83b20f5c22a869e3@group.calendar.google.com",  # ← CAMBIA ESTO
        "email": "javier.paredes@clinicassaludtotal.com",
        "horario_inicio": time(13, 0),  # 1:00 PM
        "horario_fin": time(18, 0),  # 6:00 PM
    },
}

# =============================================================================
# FIN DE CONFIGURACIÓN - NO NECESITAS EDITAR NADA DEBAJO DE ESTA LÍNEA
# =============================================================================


def generate_id() -> str:
    return str(uuid.uuid4())


def seed_clinicas_salud_total():
    """
    Cliente principal para demo: Clínicas Salud Total

    Estructura:
    - 2 sucursales con diferentes especialidades
    - 5 categorías de servicios
    - 12 servicios en total
    - 11 calendarios (empleados)
    """
    db = get_db()

    print("=" * 70)
    print("SEED DATA - mock_ai Agent Demo")
    print("=" * 70)
    print("\nCreando datos para Clínicas Salud Total...")

    # ==========================================================================
    # CLIENTE PRINCIPAL
    # ==========================================================================
    client_id = generate_id()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """INSERT OR REPLACE INTO clients (
                id, email, business_name, owner_name, phone,
                max_branches, max_calendars, max_appointments_monthly, booking_window_days,
                bot_name, greeting_message, whatsapp_number, ai_model,
                created_at, updated_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                client_id,
                "alberto.mendoza@clinicassaludtotal.com",
                "Clínicas Salud Total",
                "Alberto Mendoza",
                "+593999000001",
                5,  # max_branches
                15,  # max_calendars
                500,  # max_appointments
                30,  # booking_window_days
                "mock_ai",
                "¡Hola! Soy mock_ai, el asistente virtual de Clínicas Salud Total. ¿En qué puedo ayudarte hoy?",
                "+593912345678",
                "gpt-4o-mini",
                datetime.now(),
                datetime.now(),
                1,
            ),
        )

        print(f"\n✓ Cliente creado: {client_id}")
        print(f"  - Nombre: Clínicas Salud Total")
        print(f"  - WhatsApp: +593912345678")

        # ======================================================================
        # SUCURSAL 1: CLÍNICA CENTRO
        # ======================================================================
        branch1_id = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO branches (
                id, client_id, name, address, city,
                opening_time, closing_time, working_days, phone,
                created_at, updated_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                branch1_id,
                client_id,
                "Clínica Centro",
                "Av. 10 de Agosto N25-45 y Colón",
                "Quito",
                time(8, 0),
                time(19, 0),
                "1,2,3,4,5,6",
                "+593999100001",
                datetime.now(),
                datetime.now(),
                1,
            ),
        )

        print(f"\n✓ Sucursal 1: Clínica Centro")
        print(f"  - Dirección: Av. 10 de Agosto N25-45 y Colón")
        print(f"  - Horario: Lun-Sáb 8:00-19:00")

        # --- Categoría: Consultas Generales ---
        cat_general = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO categories (
                id, branch_id, name, description, display_order, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                cat_general,
                branch1_id,
                "Consultas Generales",
                "Atención médica general para adultos",
                1,
                datetime.now(),
                1,
            ),
        )

        svc_consulta_general = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_consulta_general,
                cat_general,
                branch1_id,
                "Consulta General",
                "Consulta médica general para diagnóstico y tratamiento",
                Decimal("20.00"),
                30,
                datetime.now(),
                1,
            ),
        )

        svc_control_general = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_control_general,
                cat_general,
                branch1_id,
                "Control Médico",
                "Seguimiento y control de tratamientos",
                Decimal("15.00"),
                20,
                datetime.now(),
                1,
            ),
        )

        svc_chequeo_preventivo = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_chequeo_preventivo,
                cat_general,
                branch1_id,
                "Chequeo Preventivo",
                "Examen médico completo preventivo anual",
                Decimal("35.00"),
                45,
                datetime.now(),
                1,
            ),
        )

        print(f"  - Categoría: Consultas Generales (3 servicios)")

        # --- Categoría: Pediatría ---
        cat_pediatria = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO categories (
                id, branch_id, name, description, display_order, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                cat_pediatria,
                branch1_id,
                "Pediatría",
                "Atención médica especializada para niños y adolescentes",
                2,
                datetime.now(),
                1,
            ),
        )

        svc_consulta_pediatrica = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_consulta_pediatrica,
                cat_pediatria,
                branch1_id,
                "Consulta Pediátrica",
                "Consulta médica para niños y adolescentes",
                Decimal("25.00"),
                30,
                datetime.now(),
                1,
            ),
        )

        svc_control_nino_sano = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_control_nino_sano,
                cat_pediatria,
                branch1_id,
                "Control de Niño Sano",
                "Seguimiento del desarrollo y crecimiento infantil",
                Decimal("18.00"),
                25,
                datetime.now(),
                1,
            ),
        )

        print(f"  - Categoría: Pediatría (2 servicios)")

        # --- Categoría: Cardiología ---
        cat_cardiologia = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO categories (
                id, branch_id, name, description, display_order, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                cat_cardiologia,
                branch1_id,
                "Cardiología",
                "Atención especializada del corazón y sistema cardiovascular",
                3,
                datetime.now(),
                1,
            ),
        )

        svc_consulta_cardio = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_consulta_cardio,
                cat_cardiologia,
                branch1_id,
                "Consulta Cardiológica",
                "Evaluación especializada del sistema cardiovascular",
                Decimal("40.00"),
                40,
                datetime.now(),
                1,
            ),
        )

        svc_electro = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_electro,
                cat_cardiologia,
                branch1_id,
                "Electrocardiograma",
                "Estudio de la actividad eléctrica del corazón",
                Decimal("30.00"),
                20,
                datetime.now(),
                1,
            ),
        )

        print(f"  - Categoría: Cardiología (2 servicios)")

        # --- Calendarios Sucursal 1 ---
        def crear_calendario(key: str, branch_id: str) -> str:
            """Crea un calendario usando la configuración del diccionario CALENDARIOS"""
            cal = CALENDARIOS[key]
            cal_id = generate_id()
            cursor.execute(
                """INSERT OR REPLACE INTO calendars (
                    id, branch_id, name, google_calendar_id, google_account_email,
                    default_start_time, default_end_time, created_at, updated_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cal_id,
                    branch_id,
                    cal["nombre"],
                    cal["google_calendar_id"],
                    cal["email"],
                    cal["horario_inicio"],
                    cal["horario_fin"],
                    datetime.now(),
                    datetime.now(),
                    1,
                ),
            )
            return cal_id

        def vincular_servicios(calendar_id: str, service_ids: list):
            """Vincula un calendario con múltiples servicios"""
            for svc_id in service_ids:
                cursor.execute(
                    "INSERT OR REPLACE INTO calendar_services (id, calendar_id, service_id, created_at) VALUES (?, ?, ?, ?)",
                    (generate_id(), calendar_id, svc_id, datetime.now()),
                )

        # Crear calendarios Sucursal 1
        cal_mario = crear_calendario("mario_gomez", branch1_id)
        vincular_servicios(
            cal_mario,
            [svc_consulta_general, svc_control_general, svc_chequeo_preventivo],
        )

        cal_laura = crear_calendario("laura_rodriguez", branch1_id)
        vincular_servicios(cal_laura, [svc_consulta_general, svc_control_general])

        cal_susana = crear_calendario("susana_torres", branch1_id)
        vincular_servicios(cal_susana, [svc_consulta_pediatrica, svc_control_nino_sano])

        cal_pedro = crear_calendario("pedro_morales", branch1_id)
        vincular_servicios(cal_pedro, [svc_consulta_pediatrica, svc_control_nino_sano])

        cal_roberto = crear_calendario("roberto_vega", branch1_id)
        vincular_servicios(cal_roberto, [svc_consulta_cardio, svc_electro])

        cal_carmen = crear_calendario("carmen_diaz", branch1_id)
        vincular_servicios(cal_carmen, [svc_consulta_cardio, svc_electro])

        print(f"  - Calendarios: 6 empleados")

        # ======================================================================
        # SUCURSAL 2: CLÍNICA NORTE
        # ======================================================================
        branch2_id = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO branches (
                id, client_id, name, address, city,
                opening_time, closing_time, working_days, phone,
                created_at, updated_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                branch2_id,
                client_id,
                "Clínica Norte",
                "Av. de la Prensa N58-120 y Río Coca",
                "Quito",
                time(9, 0),
                time(18, 0),
                "1,2,3,4,5",
                "+593999100002",
                datetime.now(),
                datetime.now(),
                1,
            ),
        )

        print(f"\n✓ Sucursal 2: Clínica Norte")
        print(f"  - Dirección: Av. de la Prensa N58-120 y Río Coca")
        print(f"  - Horario: Lun-Vie 9:00-18:00")

        # --- Categoría: Servicios Dentales ---
        cat_dental = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO categories (
                id, branch_id, name, description, display_order, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                cat_dental,
                branch2_id,
                "Servicios Dentales",
                "Atención odontológica integral",
                1,
                datetime.now(),
                1,
            ),
        )

        svc_limpieza = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_limpieza,
                cat_dental,
                branch2_id,
                "Limpieza Dental",
                "Limpieza dental profesional con ultrasonido",
                Decimal("30.00"),
                30,
                datetime.now(),
                1,
            ),
        )

        svc_curacion = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_curacion,
                cat_dental,
                branch2_id,
                "Curación Dental",
                "Tratamiento y restauración de caries",
                Decimal("25.00"),
                25,
                datetime.now(),
                1,
            ),
        )

        svc_revision_dental = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_revision_dental,
                cat_dental,
                branch2_id,
                "Revisión Dental",
                "Examen dental completo con diagnóstico",
                Decimal("15.00"),
                20,
                datetime.now(),
                1,
            ),
        )

        print(f"  - Categoría: Servicios Dentales (3 servicios)")

        # --- Categoría: Dermatología ---
        cat_dermato = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO categories (
                id, branch_id, name, description, display_order, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                cat_dermato,
                branch2_id,
                "Dermatología",
                "Cuidado especializado de la piel",
                2,
                datetime.now(),
                1,
            ),
        )

        svc_consulta_dermato = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_consulta_dermato,
                cat_dermato,
                branch2_id,
                "Consulta Dermatológica",
                "Evaluación completa de la piel",
                Decimal("35.00"),
                30,
                datetime.now(),
                1,
            ),
        )

        svc_tratamiento_acne = generate_id()
        cursor.execute(
            """INSERT OR REPLACE INTO services (
                id, category_id, branch_id, name, description, price, duration_minutes,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                svc_tratamiento_acne,
                cat_dermato,
                branch2_id,
                "Tratamiento de Acné",
                "Tratamiento especializado para el acné",
                Decimal("45.00"),
                40,
                datetime.now(),
                1,
            ),
        )

        print(f"  - Categoría: Dermatología (2 servicios)")

        # --- Calendarios Sucursal 2 ---
        cal_maria = crear_calendario("maria_lopez", branch2_id)
        vincular_servicios(cal_maria, [svc_limpieza, svc_curacion, svc_revision_dental])

        cal_carlos = crear_calendario("carlos_andrade", branch2_id)
        vincular_servicios(cal_carlos, [svc_limpieza, svc_curacion])

        cal_felipe = crear_calendario("felipe_herrera", branch2_id)
        vincular_servicios(
            cal_felipe, [svc_limpieza, svc_curacion, svc_revision_dental]
        )

        cal_ana = crear_calendario("ana_martinez", branch2_id)
        vincular_servicios(cal_ana, [svc_consulta_dermato, svc_tratamiento_acne])

        cal_javier = crear_calendario("javier_paredes", branch2_id)
        vincular_servicios(cal_javier, [svc_consulta_dermato, svc_tratamiento_acne])

        print(f"  - Calendarios: 5 empleados")

    # ==========================================================================
    # RESUMEN FINAL
    # ==========================================================================
    print("\n" + "=" * 70)
    print("SEED COMPLETADO EXITOSAMENTE")
    print("=" * 70)

    print(
        f"""
📋 RESUMEN DE DATOS CREADOS:

🏢 Cliente: Clínicas Salud Total
   └─ ID: {client_id}
   └─ WhatsApp: +593912345678

📍 Sucursal 1: Clínica Centro (Av. 10 de Agosto)
   └─ Horario: Lun-Sáb 8:00-19:00
   └─ Categorías:
      ├─ Consultas Generales: Consulta General, Control Médico, Chequeo Preventivo
      ├─ Pediatría: Consulta Pediátrica, Control de Niño Sano
      └─ Cardiología: Consulta Cardiológica, Electrocardiograma
   └─ Empleados (6):
      ├─ Dr. Mario Gómez (Medicina General) - 8:00-16:00
      ├─ Dra. Laura Rodríguez (Medicina General) - 10:00-18:00
      ├─ Dra. Susana Torres (Pediatría) - 8:00-14:00
      ├─ Dr. Pedro Morales (Pediatría) - 14:00-19:00
      ├─ Dr. Roberto Vega (Cardiología) - 9:00-17:00
      └─ Dra. Carmen Díaz (Cardiología) - 11:00-18:00

📍 Sucursal 2: Clínica Norte (Av. de la Prensa)
   └─ Horario: Lun-Vie 9:00-18:00
   └─ Categorías:
      ├─ Servicios Dentales: Limpieza, Curación, Revisión Dental
      └─ Dermatología: Consulta Dermatológica, Tratamiento de Acné
   └─ Empleados (5):
      ├─ Dra. María López (Odontología) - 9:00-17:00
      ├─ Dr. Carlos Andrade (Odontología) - 12:00-18:00
      ├─ Dr. Felipe Herrera (Odontología) - 9:00-14:00
      ├─ Dra. Ana Martínez (Dermatología) - 9:00-16:00
      └─ Dr. Javier Paredes (Dermatología) - 13:00-18:00

📊 TOTALES:
   └─ 1 Cliente
   └─ 2 Sucursales
   └─ 5 Categorías
   └─ 12 Servicios
   └─ 11 Calendarios (empleados)

⚠️  RECUERDA: Edita el diccionario CALENDARIOS al inicio del archivo
    para poner los Google Calendar IDs reales de cada empleado.
"""
    )

    return client_id


def seed_all():
    """Ejecutar seed principal"""
    return seed_clinicas_salud_total()


if __name__ == "__main__":
    seed_all()
