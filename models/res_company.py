from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ResCompany(models.Model):
    _inherit = 'res.company'

    report_header_image = fields.Binary(
        string="Custom Report Header Image",
        attachment=True,
        help="Upload a custom header image for PDF reports. "
             "Recommended: 1800x300 pixels (6:1 ratio), PNG or JPG format, max 5MB. "
             "If set and enabled, this will replace the standard Odoo header in all PDF reports."
    )
    
    use_custom_report_header = fields.Boolean(
        string="Use Custom Report Header",
        default=False,
        help="Enable this to use the custom header image instead of the standard Odoo header in PDF reports."
    )
    
    report_header_image_filename = fields.Char(
        string="Header Image Filename",
        help="Filename of the uploaded header image"
    )

    @api.constrains('report_header_image')
    def _check_report_header_image(self):
        """Validate the uploaded header image"""
        if not PIL_AVAILABLE:
            return  # Skip validation if PIL is not available
            
        for company in self:
            if company.report_header_image:
                try:
                    # Decode the image
                    image_data = base64.b64decode(company.report_header_image)
                    
                    # Check file size (5MB limit)
                    file_size_mb = len(image_data) / (1024 * 1024)
                    if file_size_mb > 5:
                        raise ValidationError(
                            f"Header image is too large ({file_size_mb:.1f}MB). "
                            "Maximum size is 5MB. Please compress the image."
                        )
                    
                    # Open with PIL to validate and check dimensions
                    image = Image.open(BytesIO(image_data))
                    width, height = image.size
                    
                    # Warn if dimensions are too small
                    if width < 1200:
                        raise ValidationError(
                            f"Header image width is {width}px. "
                            "Recommended minimum is 1200px for good print quality. "
                            "Please upload a higher resolution image."
                        )
                    
                    # Check aspect ratio (warn if not close to 6:1)
                    ratio = width / height if height > 0 else 0
                    if ratio < 4 or ratio > 8:
                        # Just a warning, don't block
                        pass  # Could log a warning here
                        
                except Exception as e:
                    raise ValidationError(
                        f"Invalid image file. Please upload a valid PNG or JPG image. Error: {str(e)}"
                    )
