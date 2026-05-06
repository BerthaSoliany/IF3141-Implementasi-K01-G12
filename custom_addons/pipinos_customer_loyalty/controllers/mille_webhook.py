import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class MilleWebhook(http.Controller):

    @http.route('/mille/transaksi', type='json', auth='none', methods=['POST'], csrf=False)
    def receive_transaksi(self, **kwargs):
        """
        Terima data transaksi dari Mille.
        Payload: {
            "no_hp": "08123456789",
            "tanggal": "2026-05-05T13:00:00",  (opsional)
            "items": [
                {"id_menu": "MNU001", "qty": 2, "subtotal": 50000}
            ],
            "total_nominal": 50000
        }
        """
        try:
            no_hp = (kwargs.get('no_hp') or '').strip()
            if not no_hp:
                return {'status': 'error', 'message': 'no_hp wajib diisi'}

            env = request.env(user=1)

            pengunjung = env['pipinos.pengunjung'].search([('no_hp', '=', no_hp)], limit=1)
            if not pengunjung:
                return {'status': 'error', 'message': f'Pengunjung dengan no_hp {no_hp} tidak ditemukan'}

            tanggal = kwargs.get('tanggal') or fields.Datetime.now()

            transaksi = env['pipinos.transaksi'].create({
                'id_pengunjung': pengunjung.id,
                'tanggal': tanggal,
            })

            for item in (kwargs.get('items') or []):
                id_menu_str = item.get('id_menu', '')
                menu = env['pipinos.item.menu'].search([('id_menu', '=', id_menu_str)], limit=1)
                env['pipinos.detail.transaksi'].create({
                    'id_transaksi': transaksi.id,
                    'id_menu': menu.id if menu else False,
                    'qty': int(item.get('qty', 0)),
                    'subtotal': float(item.get('subtotal', 0)),
                })

            return {
                'status': 'sukses',
                'id_transaksi': transaksi.id_transaksi,
                'id_pengunjung': pengunjung.id_pengunjung,
            }

        except Exception as e:
            _logger.exception('Error receive_transaksi dari Mille')
            return {'status': 'error', 'message': str(e)}

    @http.route('/mille/menu', type='json', auth='none', methods=['POST'], csrf=False)
    def receive_menu(self, **kwargs):
        """
        Terima data menu dari Mille. Create jika belum ada, update jika sudah ada.
        Payload: [
            {"id_menu": "MNU001", "nama_menu": "Ayam Bakar", "harga": 25000, "kategori": "Makanan"}
        ]
        """
        try:
            items = kwargs.get('items') or []
            if not isinstance(items, list):
                return {'status': 'error', 'message': 'Field items harus berupa array'}

            env = request.env(user=1)
            dibuat = 0
            diupdate = 0

            for item in items:
                id_menu_str = item.get('id_menu', '').strip()
                if not id_menu_str:
                    continue

                existing = env['pipinos.item.menu'].search([('id_menu', '=', id_menu_str)], limit=1)
                vals = {
                    'nama_menu': item.get('nama_menu', ''),
                    'harga': float(item.get('harga', 0)),
                    'kategori': item.get('kategori', ''),
                }
                if existing:
                    existing.write(vals)
                    diupdate += 1
                else:
                    vals['id_menu'] = id_menu_str
                    env['pipinos.item.menu'].create(vals)
                    dibuat += 1

            return {
                'status': 'sukses',
                'dibuat': dibuat,
                'diupdate': diupdate,
            }

        except Exception as e:
            _logger.exception('Error receive_menu dari Mille')
            return {'status': 'error', 'message': str(e)}
