import django.db.models.deletion
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('products', '0001_initial'),
        ('suppliers', '0001_initial'),
        ('transactional', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Stock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.DecimalField(decimal_places=3, default=0, max_digits=12,
                                                 validators=[django.core.validators.MinValueValidator(0)],
                                                 verbose_name='Cantidad')),
                ('creado_en', models.DateTimeField(auto_now_add=True, verbose_name='Creado en')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               to='products.producto', verbose_name='Producto')),
                ('bodega', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             to='transactional.bodega', verbose_name='Bodega')),
            ],
            options={
                'verbose_name': 'Stock',
                'verbose_name_plural': 'Stocks',
                'ordering': ['producto'],
                'indexes': [
                    models.Index(fields=['producto'], name='transaction_producto_idx'),
                    models.Index(fields=['bodega'], name='transaction_bodega_idx'),
                ],
                'constraints': [
                    models.CheckConstraint(
                        check=models.Q(cantidad__gte=0),
                        name='stock_cantidad_ge_0'
                    ),
                ],
            },
        ),
    ]
