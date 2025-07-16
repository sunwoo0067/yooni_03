"""
1688 커넥터 테스트 명령어
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from suppliers.models import Supplier
from suppliers.connectors.factory import create_connector


class Command(BaseCommand):
    help = '1688 (Alibaba) 커넥터 연결 및 기능 테스트'

    def add_arguments(self, parser):
        parser.add_argument(
            '--supplier-id',
            type=int,
            help='테스트할 공급업체 ID'
        )
        parser.add_argument(
            '--search',
            type=str,
            help='제품 검색 테스트 (검색어 입력)'
        )
        parser.add_argument(
            '--product-id',
            type=str,
            help='특정 제품 상세정보 조회 테스트'
        )
        parser.add_argument(
            '--sync-product',
            type=str,
            help='제품 데이터 동기화 테스트'
        )
        parser.add_argument(
            '--create-test-supplier',
            action='store_true',
            help='테스트용 1688 공급업체 생성'
        )

    def handle(self, *args, **options):
        try:
            # 테스트용 공급업체 생성
            if options['create_test_supplier']:
                self.create_test_supplier()
                return

            # 공급업체 가져오기
            supplier = self.get_supplier(options.get('supplier_id'))
            if not supplier:
                return

            # 커넥터 생성
            try:
                connector = create_connector(supplier)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 커넥터 생성 성공: {connector.__class__.__name__}')
                )
            except Exception as e:
                raise CommandError(f'커넥터 생성 실패: {e}')

            # 연결 테스트
            self.test_connection(connector)

            # 제품 검색 테스트
            if options.get('search'):
                self.test_product_search(connector, options['search'])

            # 제품 상세정보 테스트
            if options.get('product_id'):
                self.test_product_details(connector, options['product_id'])

            # 제품 동기화 테스트
            if options.get('sync_product'):
                self.test_product_sync(connector, options['sync_product'])

        except Exception as e:
            raise CommandError(f'테스트 실행 중 오류 발생: {e}')

    def get_supplier(self, supplier_id):
        """공급업체 조회"""
        if supplier_id:
            try:
                supplier = Supplier.objects.get(id=supplier_id)
                self.stdout.write(f'📋 공급업체: {supplier.name} (ID: {supplier.id})')
                return supplier
            except Supplier.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ 공급업체 ID {supplier_id}를 찾을 수 없습니다.')
                )
                return None
        else:
            # 1688 공급업체 자동 찾기
            suppliers = Supplier.objects.filter(
                connection_settings__connector_type='alibaba_1688'
            ).first()
            
            if not suppliers:
                suppliers = Supplier.objects.filter(code__in=['alibaba', '1688']).first()
            
            if suppliers:
                self.stdout.write(f'📋 자동 선택된 공급업체: {suppliers.name} (ID: {suppliers.id})')
                return suppliers
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  1688 공급업체를 찾을 수 없습니다. '
                        '--create-test-supplier 옵션으로 테스트 공급업체를 생성하세요.'
                    )
                )
                return None

    def create_test_supplier(self):
        """테스트용 1688 공급업체 생성"""
        # 테스트용 자격증명 (평문으로 저장 후 암호화됨)
        test_credentials = {
            'app_key': 'your_1688_app_key_here',
            'app_secret': 'your_1688_app_secret_here',
            'access_token': 'your_1688_access_token_here'
        }
        
        supplier, created = Supplier.objects.get_or_create(
            code='1688_test',
            defaults={
                'name': '1688 테스트 공급업체',
                'description': '1688 API 테스트를 위한 공급업체',
                'connector_type': 'api',
                'api_base_url': 'https://gw.open.1688.com/openapi',
                'connection_settings': {
                    'connector_type': 'alibaba_1688',
                    'rate_limit_per_minute': 60,
                    'timeout_seconds': 30
                },
                'status': 'testing',
                'is_auto_sync_enabled': False,
                'sync_frequency_hours': 24
            }
        )
        
        # 자격증명 설정
        if created:
            supplier.set_credentials(test_credentials)

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ 테스트 공급업체가 생성되었습니다: {supplier.name} (ID: {supplier.id})'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  실제 1688 API 자격증명을 설정해야 합니다:\n'
                    '   1. Django Admin에서 공급업체 편집\n'
                    '   2. credentials 필드에 실제 API 키 입력\n'
                    '   3. app_key, app_secret, access_token 설정'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  테스트 공급업체가 이미 존재합니다: {supplier.name} (ID: {supplier.id})'
                )
            )

    def test_connection(self, connector):
        """연결 테스트"""
        self.stdout.write('\n🔍 연결 테스트 중...')
        
        # 기본 연결 테스트
        is_connected, error_msg = connector.test_connection()
        
        if is_connected:
            self.stdout.write(self.style.SUCCESS('✅ 연결 성공!'))
            
            # 상세 연결 정보 조회 (1688 커넥터만)
            if hasattr(connector, 'test_connection_detailed'):
                detailed_result = connector.test_connection_detailed()
                if detailed_result.get('success'):
                    self.stdout.write(
                        f'   응답시간: {detailed_result.get("response_time", 0):.2f}초'
                    )
                    if 'account_info' in detailed_result:
                        self.stdout.write(f'   계정 정보: {detailed_result["account_info"]}')
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ 연결 실패: {error_msg}')
            )

    def test_product_search(self, connector, search_query):
        """제품 검색 테스트"""
        self.stdout.write(f'\n🔍 제품 검색 테스트: "{search_query}"')
        
        try:
            products = connector.fetch_products(
                search_text=search_query,
                page_size=5
            )
            
            if products:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {len(products)}개 제품을 찾았습니다:')
                )
                
                for i, product in enumerate(products, 1):
                    self.stdout.write(
                        f'   {i}. {product.get("name", "이름 없음")} '
                        f'(ID: {product.get("supplier_product_id", "N/A")})'
                    )
                    self.stdout.write(
                        f'      가격: {product.get("price", {}).get("amount", 0)} '
                        f'{product.get("price", {}).get("currency", "CNY")}'
                    )
                    self.stdout.write(
                        f'      공급업체: {product.get("supplier_info", {}).get("company_name", "N/A")}'
                    )
                    self.stdout.write('')
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  검색 결과가 없습니다.')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 제품 검색 실패: {e}')
            )

    def test_product_details(self, connector, product_id):
        """제품 상세정보 테스트"""
        self.stdout.write(f'\n🔍 제품 상세정보 조회: {product_id}')
        
        try:
            details = connector.get_product_details(product_id)
            
            if details:
                self.stdout.write(
                    self.style.SUCCESS('✅ 제품 상세정보 조회 성공:')
                )
                self.stdout.write(f'   이름: {details.get("name", "N/A")}')
                self.stdout.write(f'   카테고리: {details.get("category", "N/A")}')
                self.stdout.write(f'   브랜드: {details.get("brand", "N/A")}')
                self.stdout.write(f'   설명: {details.get("description", "N/A")[:100]}...')
                
                # 가격 정보 테스트
                price_info = connector.get_product_price(product_id)
                if price_info:
                    self.stdout.write(
                        f'   가격: {price_info.get("unit_price", 0)} '
                        f'{price_info.get("currency", "CNY")}'
                    )
                    self.stdout.write(
                        f'   최소주문수량: {price_info.get("min_order_quantity", 1)}'
                    )
                
                # 재고 정보 테스트
                inventory = connector.get_inventory(product_id)
                if inventory:
                    self.stdout.write(
                        f'   재고: {inventory.get("available_quantity", 0)}개'
                    )
                    
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  제품 상세정보를 찾을 수 없습니다.')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 제품 상세정보 조회 실패: {e}')
            )

    def test_product_sync(self, connector, product_id):
        """제품 동기화 테스트"""
        self.stdout.write(f'\n🔄 제품 동기화 테스트: {product_id}')
        
        try:
            success = connector.sync_product_data(product_id)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS('✅ 제품 데이터 동기화 성공!')
                )
                
                # 동기화된 데이터 확인
                from suppliers.models import SupplierProduct
                try:
                    product = SupplierProduct.objects.get(
                        supplier=connector.supplier,
                        supplier_product_id=product_id
                    )
                    self.stdout.write(f'   제품명: {product.name}')
                    self.stdout.write(f'   가격: {product.cost_price} {product.currency}')
                    self.stdout.write(f'   재고: {product.available_quantity}개')
                    self.stdout.write(f'   상태: {product.status}')
                    self.stdout.write(f'   마지막 동기화: {product.last_sync_at}')
                    
                except SupplierProduct.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING('⚠️  동기화된 제품 데이터를 찾을 수 없습니다.')
                    )
                    
            else:
                self.stdout.write(
                    self.style.ERROR('❌ 제품 데이터 동기화 실패')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 제품 동기화 실행 실패: {e}')
            )