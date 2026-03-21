from etl.fcc_fabric_loader import load_fabric
from etl.bdc_loader import load_bdc

class ETLService:
    """Service for managing ETL operations"""
    
    @staticmethod
    def load_fabric_data(file_path):
        """Load FCC fabric data from CSV"""
        try:
            load_fabric(file_path)
            return {"status": "success", "message": "Fabric data loaded"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def load_bdc_data(file_path):
        """Load BDC data from file"""
        try:
            load_bdc(file_path)
            return {"status": "success", "message": "BDC data loaded"}
        except Exception as e:
            return {"status": "error", "message": str(e)}