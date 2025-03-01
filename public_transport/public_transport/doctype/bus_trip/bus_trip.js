frappe.ui.form.on('Bus Trip', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {  // If submitted
            frm.add_custom_button(__('View Bookings'), function() {
                frappe.set_route('List', 'Booking', {bus_trip: frm.doc.name});
            });
        }
    },
    
    long_trip_limited_seat: function(frm) {
        // Toggle seat map section based on long trip toggle
        frm.toggle_reqd('seat_map_layout', frm.doc.long_trip_limited_seat);
    },
    
    bus: function(frm) {
        if (frm.doc.bus) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Bus',
                    name: frm.doc.bus
                },
                callback: function(r) {
                    if (r.message && r.message.capacity) {
                        // Set indicator if seat map exceeds capacity
                        if (frm.doc.seat_map_layout && 
                            frm.doc.seat_map_layout.length > r.message.capacity) {
                            frappe.show_alert({
                                message: __('Seat map exceeds bus capacity'),
                                indicator: 'red'
                            });
                        }
                    }
                }
            });
        }
    }
});