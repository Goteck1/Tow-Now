# 🛣️ TowNow - Roadmap de Desarrollo

Este roadmap detalla las tareas técnicas y funcionales planificadas para el desarrollo y evolución de la plataforma TowNow.

| Módulo / Área         | Tarea                                                                 | Estado        | Prioridad | Notas                                                             |
|-----------------------|------------------------------------------------------------------------|---------------|-----------|-------------------------------------------------------------------|
| 🔧 Infraestructura     | Migrar de MySQL a PostgreSQL                                           | ✅ Hecho       | Alta      | Ya está funcionando en Render                                     |
| 🔧 Infraestructura     | Despliegue automático en Render                                        | ✅ Hecho       | Alta      | Proyecto en línea: https://tow-now.onrender.com                   |
| 👤 Clientes            | Flujo de solicitud de grúa en 3 pasos                                 | ✅ Hecho       | Alta      | Funcional con geolocalización y tipos de vehículo                 |
| 👤 Clientes            | Historial de servicios del cliente                                     | 🔄 En progreso | Alta      | El botón está, falta completar la lógica                          |
| 👤 Clientes            | Editar perfil del cliente                                              | 🕒 Pendiente   | Media     | Nombre, email, teléfono                                           |
| 👤 Clientes            | Mostrar información de pago anterior                                  | 🕒 Pendiente   | Media     | Depende de integración con Stripe                                 |
| 🚛 Proveedores         | Dashboard con solicitudes asignadas                                   | ✅ Hecho       | Alta      | Vista inicial creada                                              |
| 🚛 Proveedores         | Recepción de nuevas solicitudes (alertas)                             | 🕒 Pendiente   | Alta      | Push/Polling o WebSocket, aún no implementado                     |
| 🚛 Proveedores         | Confirmar, rechazar o actualizar estado de un servicio                | 🕒 Pendiente   | Alta      | Crucial para operación real                                       |
| 💳 Pagos               | Integrar Stripe para pagos                                             | 🕒 Pendiente   | Alta      | Checkout funcional, cambio de estado a “Paid”                    |
| 💳 Pagos               | Guardar y mostrar métodos de pago del cliente                         | 🕒 Pendiente   | Media     | Opcional, útil para clientes recurrentes                          |
| 📍 Precios             | Implementar fórmula de precios dinámica por distancia, tiempo y tipo  | ✅ Hecho       | Alta      | Ya funcional, configurable desde el backend                       |
| 📍 Precios             | Editor interno para coeficientes desde el admin                       | 🕒 Pendiente   | Baja      | Permitir modificar coeficientes sin tocar el código              |
| 🧑‍💼 Admin              | Panel con conteo de usuarios y servicios                              | ✅ Hecho       | Alta      | Ya disponible                                                      |
| 🧑‍💼 Admin              | Vista detallada de cada solicitud y edición manual                   | 🕒 Pendiente   | Media     | Útil para soporte                                                 |
| ✉ Notificaciones       | Enviar confirmación por email o SMS al cliente                        | 🕒 Pendiente   | Media     | Usar SendGrid o Twilio en el futuro                               |
| 📱 UX/UI               | Mejorar encabezado, copy, claridad de flujo                          | ✅ Hecho       | Alta      | Rediseñado con branding claro                                     |
| 📱 UX/UI               | Agregar CTA de WhatsApp o contacto directo                           | 🕒 Pendiente   | Alta      | Importante para confianza de nuevos usuarios                      |

---

✍️ Este documento debe mantenerse actualizado manualmente conforme avances.

👉 Siguiente paso sugerido: Priorizar tareas "Pendiente" según valor comercial inmediato.
