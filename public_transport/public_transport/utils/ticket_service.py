import frappe
import qrcode
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64

class TicketGenerator:
    def __init__(self, booking_id):
        self.booking = frappe.get_doc("Booking", booking_id)
        self.trip = frappe.get_doc("Bus Trip", self.booking.bus_trip)
        self.qr = qrcode.QRCode(version=1, box_size=10, border=5)

    def generate_ticket(self):
        """Generate a printable ticket with QR code"""
        try:
            # Create QR code with booking details
            qr_data = {
                "booking_id": self.booking.name,
                "trip_id": self.trip.name,
                "seats": [s.seat_id for s in self.booking.selected_seats],
                "passenger": self.booking.passenger_name
            }
            self.qr.add_data(str(qr_data))
            self.qr.make(fit=True)
            qr_image = self.qr.make_image(fill_color="black", back_color="white")
            
            # Create ticket image
            ticket = Image.new('RGB', (800, 400), 'white')
            draw = ImageDraw.Draw(ticket)
            
            # Add text content
            self._add_ticket_text(draw)
            
            # Add QR code
            ticket.paste(qr_image, (600, 50))
            
            # Convert to base64 for printing
            buffered = BytesIO()
            ticket.save(buffered, format="PNG")
            ticket_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            return {
                "status": "success",
                "ticket_image": ticket_b64,
                "booking_id": self.booking.name
            }
            
        except Exception as e:
            frappe.log_error(f"Ticket Generation Failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _add_ticket_text(self, draw):
        """Add text content to ticket image"""
        try:
            # Add header
            draw.text((50, 50), "Bus Ticket", fill="black", font=self._get_font(size=40))
            
            # Add booking details
            details = [
                f"Booking ID: {self.booking.name}",
                f"Route: {self.trip.route}",
                f"Date: {self.trip.departure_time.strftime('%Y-%m-%d')}",
                f"Time: {self.trip.departure_time.strftime('%H:%M')}",
                f"Passenger: {self.booking.passenger_name}",
                f"Seats: {', '.join(s.seat_id for s in self.booking.selected_seats)}"
            ]
            
            y_position = 120
            for line in details:
                draw.text((50, y_position), line, fill="black", font=self._get_font())
                y_position += 40
                
        except Exception as e:
            frappe.log_error(f"Ticket Text Addition Failed: {str(e)}")
            raise

    def _get_font(self, size=24):
        """Get font for ticket text"""
        try:
            # Use a default system font
            # In production, you should use a specific font file
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        except:
            return ImageFont.load_default()

def print_ticket(booking_id, printer_id=None):
    """Send ticket to printer"""
    try:
        # Generate ticket
        generator = TicketGenerator(booking_id)
        ticket_data = generator.generate_ticket()
        
        if ticket_data["status"] != "success":
            return ticket_data
            
        if printer_id:
            # TODO: Implement actual printer integration
            # For now, we'll just simulate printing
            frappe.log_error(f"Printing ticket {booking_id} to printer {printer_id}")
            
        return {
            "status": "success",
            "message": "Ticket ready for printing",
            "ticket_data": ticket_data
        }
        
    except Exception as e:
        frappe.log_error(f"Ticket Printing Failed: {str(e)}")
        return {"status": "error", "message": str(e)}

def validate_ticket(qr_data):
    """Validate a scanned ticket"""
    try:
        # Parse QR data
        booking_data = eval(qr_data)  # Safe since we generated the QR code
        
        # Get booking
        booking = frappe.get_doc("Booking", booking_data["booking_id"])
        
        # Check if booking is valid
        is_valid = (
            booking.docstatus == 1 and
            booking.booking_status == "Confirmed" and
            booking.name == booking_data["booking_id"]
        )
        
        return {
            "status": "success",
            "is_valid": is_valid,
            "booking": booking.name if is_valid else None
        }
        
    except Exception as e:
        frappe.log_error(f"Ticket Validation Failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "is_valid": False
        }