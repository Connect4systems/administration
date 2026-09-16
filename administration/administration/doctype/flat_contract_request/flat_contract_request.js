// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

const default_english_terms = `
<h3>Article One - Preamble</h3>
<p>The above preamble and the information recorded in this contract form an integral part of this agreement.</p>
<h3>Article Two - Purpose of Lease</h3>
<p>The Second Party (the Lessor) leases the residential unit described in this contract to the First Party (the Lessee) for accommodation of the company's employees. The unit may not be altered or used for any purpose other than the agreed residential purpose.</p>
<h3>Article Three - Furnishings and Contents</h3>
<p>The parties shall record the condition and contents of the leased premises in the contents table attached to this contract.</p>
<h3>Article Four - Lease Term</h3>
<p>The lease starts on the contract start date and ends on the contract end date. Any renewal shall be agreed in a new written contract.</p>
<h3>Article Five - Rent and Payment Terms</h3>
<p>The rent is payable according to the payment cycle recorded above. The First Party shall pay the agreed rent and any applicable charges to the bank account stated in this contract.</p>
<h3>Article Six - Security Deposit and Insurance</h3>
<p>The security deposit and insurance amount are held according to the agreed terms and shall be settled after handover, subject to any lawful deductions for damage or outstanding amounts.</p>
<h3>Article Seven - Handover and Maintenance</h3>
<p>The First Party shall inspect and receive the leased premises in its recorded condition and shall maintain it with reasonable care throughout the lease term.</p>
<h3>Article Eight - Termination and Jurisdiction</h3>
<p>Termination, notices, and disputes shall be handled according to the applicable laws and the written terms of this agreement.</p>
<h3>Article Nine - Contract Copies</h3>
<p>This contract is made in two original copies, one for each party.</p>`;

const default_arabic_terms = `
<h3>البند الأول - التمهيد</h3>
<p>يعتبر التمهيد والبيانات الواردة في هذا العقد جزءاً لا يتجزأ منه ومكملاً ومفسراً لشروطه.</p>
<h3>البند الثاني - الغرض من الإيجار</h3>
<p>يؤجر الطرف الثاني (المؤجر) للطرف الأول (المستأجر) الوحدة السكنية الموضحة في هذا العقد بغرض استخدامها كسكن خاص بالعاملين لدى الشركة، ولا يجوز تغيير استخدامها أو إجراء تعديلات عليها إلا بموافقة كتابية.</p>
<h3>البند الثالث - المنقولات والمحتويات</h3>
<p>يتفق الطرفان على تسجيل حالة ومحتويات العين المؤجرة في جدول المحتويات المرفق بهذا العقد.</p>
<h3>البند الرابع - مدة الإيجار</h3>
<p>تبدأ مدة الإيجار من تاريخ بداية العقد وتنتهي في تاريخ نهاية العقد، وأي تجديد يكون بموجب عقد كتابي جديد.</p>
<h3>البند الخامس - القيمة الإيجارية وطريقة السداد</h3>
<p>تسدد القيمة الإيجارية وفقاً لدورة السداد الموضحة أعلاه، ويلتزم الطرف الأول بسداد القيمة والمبالغ المستحقة على الحساب البنكي المبين في هذا العقد.</p>
<h3>البند السادس - التأمين والوديعة</h3>
<p>تحتفظ الجهة المؤجرة بالتأمين والوديعة وفقاً للشروط المتفق عليها، ويتم تسويتهما عند التسليم بعد خصم أي تلفيات أو مبالغ مستحقة بصورة قانونية.</p>
<h3>البند السابع - التسليم والصيانة</h3>
<p>يقر الطرف الأول بأنه عاين العين المؤجرة وتسلمها بالحالة الموضحة، ويلتزم بالمحافظة عليها واستعمالها بعناية طوال مدة الإيجار.</p>
<h3>البند الثامن - الإنهاء والاختصاص</h3>
<p>يتم إنهاء العقد وتوجيه الإخطارات وتسوية المنازعات وفقاً للقوانين واجبة التطبيق والشروط المكتوبة في هذا العقد.</p>
<h3>البند التاسع - نسخ العقد</h3>
<p>حرر هذا العقد من نسختين أصليتين، يحتفظ كل طرف بنسخة للعمل بموجبها عند اللزوم.</p>`;

frappe.ui.form.on("Flat Contract Request", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}

		frm.add_custom_button(__("Create Flat Contract"), () => {
			frappe.model.with_doctype("Flat Contract", () => {
				const contract = frappe.model.get_new_doc("Flat Contract");
				const copied_fields = [
					"project",
					"date",
					"contract_start_date",
					"contract_end_date",
					"flat_owner",
					"owner_id",
					"attach_id",
					"governorate",
					"city",
					"area",
					"address",
					"flat_no",
					"floor_no",
					"total_flat_area",
					"no_of_rooms",
					"no_of_beds",
					"no_of_ketchen_room",
					"no_of_bathroom",
					"monthly_rent",
					"payment_cycle",
					"deposit",
					"insurance",
					"bank",
					"iban",
					"ownership_documentation",
					"notes",
				];

				copied_fields.forEach((fieldname) => {
					contract[fieldname] = frm.doc[fieldname];
				});

				contract.flat_contract_request = frm.doc.name;
				contract.first_party_name = "CSCEC International Egypt for Construction Company Co., LTD s.s.c";
				contract.first_party_address = "3rd Floor, The NOX Mall, Third Sector, North 90th Street, Fifth Settlement, New Cairo, Cairo";
				contract.first_party_representative = "Authorized Manager";
				contract.second_party_name = frm.doc.flat_owner || "";
				contract.second_party_id = frm.doc.owner_id || "";
				contract.english_terms = default_english_terms;
				contract.arabic_terms = default_arabic_terms;

				(frm.doc.flat_contents || []).forEach((row) => {
					const content = frappe.model.add_child(contract, "Flat Contents", "flat_contents");
					["item_name", "description", "qty", "image"].forEach((fieldname) => {
						content[fieldname] = row[fieldname];
					});
				});

				frappe.model.sync(contract);
				frappe.set_route("Form", "Flat Contract", contract.name);
			});
		});
	},
});
