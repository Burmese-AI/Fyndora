
# class Entry(models.Model):
#     entry_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
#     workspace = #workspace id
#     team_id = #team id
#     submitted_by = #user_team id
#     submitted_at = models.DateTimeField()
#     entry_type = models.CharField()
#     amount = models.DecimalField()
#     description = models.CharField(max_length=255)
#     status = models.CharField()
#     reviewed_by = #user_team id
#     reviewd_note = models.TextField(max_length=255)

#     class class Meta:
#         verbose_name = 'entry'
#         verbose_name_plural = 'entries'
#         ordering = ['-created_at']
