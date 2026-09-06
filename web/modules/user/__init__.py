"""Módulo de usuarios de la parte web: quién puede entrar y a qué único
módulo tiene acceso. No aparece en la navbar como Steriflow o Ferlo -no es
una funcionalidad de negocio, es la puerta de entrada a las demás-, así que
`web/registry.py` no lo mete en `WEB_MODULES`; su router se incluye aparte
en `web/app.py`, igual que la página de Home.

Sin formulario de alta: los usuarios se siembran con `seed_web_users.py`
(ver `seed.py`) en vez de registrarse solos -es la simplificación que se
pidió para esta primera versión-.
"""
