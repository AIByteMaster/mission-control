from vercel import Vercel
from app import app as flask_app

vercel_app = Vercel(flask_app)

handler = vercel_app
