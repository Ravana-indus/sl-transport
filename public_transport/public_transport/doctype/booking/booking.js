frappe.ui.form.on('Booking', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.booking_status === "Confirmed") {
            frm.add_custom_button(__('Print Ticket'), function() {
                frappe.call({
                    method: 'public_transport.public_transport.api.generate_ticket',
                    args: {
                        booking_id: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message && r.message.status === 'success') {
                            // TODO: Implement actual ticket printing
                            frappe.show_alert({
                                message: __('Ticket generated successfully'),
                                indicator: 'green'
                            });
                        }
                    }
                });
            });
            
            frm.add_custom_button(__('Send SMS'), function() {
                frappe.call({
                    method: 'public_transport.public_transport.api.send_notification',
                    args: {
                        booking_id: frm.doc.name,
                        notification_type: 'booking_confirmation'
                    },
                    callback: function(r) {
                        if (r.message && r.message.status === 'success') {
                            frappe.show_alert({
                                message: __('SMS notification queued'),
                                indicator: 'green'
                            });
                        }
                    }
                });
            });
        }
    },
    
    bus_trip: function(frm) {
        if (frm.doc.bus_trip) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Bus Trip',
                    name: frm.doc.bus_trip
                },
                callback: function(r) {
                    if (r.message) {
                        // Show available seats
                        let availableSeats = r.message.seat_map_layout.filter(
                            seat => seat.status === 'Available'
                        );
                        if (availableSeats.length === 0) {
                            frappe.show_alert({
                                message: __('No seats available for this trip'),
                                indicator: 'red'
                            });
                        }
                    }
                }
            });
        }
    },
    
    validate: function(frm) {
        if (!frm.doc.selected_seats || frm.doc.selected_seats.length === 0) {
            frappe.throw(__('Please select at least one seat'));
        }
    }
});