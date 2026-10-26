from flask import Blueprint, render_template

methodology_bp = Blueprint('methodology', __name__)


@methodology_bp.route('/methodology')
@methodology_bp.route('/about')
def index():
    """Renders comprehensive documentation on the system architecture and mathematical methodology."""
    return render_template('methodology.html')
