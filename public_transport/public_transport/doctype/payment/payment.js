frappe.ui.form.on('Payment', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 0) {  // Draft state
            if (frm.doc.payment_type === 'Card') {
                frm.add_custom_button(__('Process Card Payment'), function() {
                    // Integrate with payment gateway
                    frappe.call({
                        method: 'public_transport.public_transport.api.process_payment',
                        args: {
                            booking_id: frm.doc.booking,
                            payment_details: JSON.stringify({
                                payment_type: 'Card',
                                amount: frm.doc.amount
                            })
                        },
                        callback: function(r) {
                            if (r.message && r.message.status === 'success') {
                                frm.reload_doc();
                                frappe.show_alert({
                                    message: __('Payment processed successfully'),
                                    indicator: 'green'
                                });
                            }
                        }
                    });
                });
            }
        }
    },
    
    payment_type: function(frm) {
        // Show/hide relevant fields based on payment type
        frm.toggle_display('transaction_reference', 
            ['Card', 'NFC', 'Online'].includes(frm.doc.payment_type));
    },
    
    booking: function(frm) {
        if (frm.doc.booking) {
            frappe.model.with_doc('Booking', frm.doc.booking, function() {
                let booking = frappe.get_doc('Booking', frm.doc.booking);
                // Auto-calculate amount from selected seats
                let total = 0;
                (booking.selected_seats || []).forEach(function(seat) {
                    total += flt(seat.price);
                });
                frm.set_value('amount', total);
            });
        }
    }
});