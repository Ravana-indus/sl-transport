frappe.provide('public_transport.realtime');

public_transport.realtime = {
    init: function() {
        this.bind_events();
    },

    bind_events: function() {
        frappe.realtime.on('seat_status_update', function(data) {
            if (cur_frm && cur_frm.doctype === 'Bus Trip' && cur_frm.doc.name === data.trip) {
                cur_frm.reload_doc();
                frappe.show_alert({
                    message: `Seat ${data.seat_id} status updated to ${data.status}`,
                    indicator: 'green'
                });
            }
        });

        frappe.realtime.on('booking_confirmation', function(data) {
            frappe.show_alert({
                message: `New booking confirmed: ${data.booking_id}`,
                indicator: 'green'
            });
            if (cur_list && cur_list.doctype === 'Booking') {
                cur_list.refresh();
            }
        });

        frappe.realtime.on('gps_update', function(data) {
            if (cur_frm && cur_frm.doctype === 'Bus' && cur_frm.doc.name === data.bus) {
                frappe.show_alert({
                    message: `Bus location updated at ${data.timestamp}`,
                    indicator: 'blue'
                });
                // Update map if it exists
                if (cur_frm.map_view) {
                    cur_frm.map_view.update_location(data.latitude, data.longitude);
                }
            }
        });

        frappe.realtime.on('sms_status_update', function(data) {
            if (cur_frm && cur_frm.doctype === 'SMS Log' && cur_frm.doc.name === data.sms_id) {
                cur_frm.reload_doc();
            }
        });
    }
};

$(document).ready(function() {
    public_transport.realtime.init();
});