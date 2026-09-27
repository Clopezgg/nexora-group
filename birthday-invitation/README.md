# Invitación Cándida & Alberto — 03 octubre 2026

Implementación pública de la invitación digital personalizada.

- Frontend visual: basado en el master de Figma `ohyjcYF3wS4V6gKlSEzuuK`
- Backend/persistencia: Supabase project `sqchlnhkceztcznkjctg`
- Endpoint público: `/functions/v1/birthday-invitation`
- Invitaciones: 100 tokens persistentes
- Asignación: 60 Cándida / 40 Alberto
- RSVP: público, sin login, una invitación por token y actualizable
- Admin: protegido por token secreto almacenado como hash en Supabase
- Google Maps: dirección 8261 SW 8th St, North Lauderdale, FL 33068
- Fecha: sábado 3 de octubre de 2026, 8:00 PM

El token nunca contiene el nombre del invitado y la asignación se resuelve en servidor.
