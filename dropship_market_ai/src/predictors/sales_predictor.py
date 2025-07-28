"""Deep learning based sales prediction system"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import structlog

from ..database.models import (
    Product, ProductPerformance, AIPrediction,
    Review, MarketOptimization
)
from ..utils.cache import RedisCache, CacheKey

logger = structlog.get_logger()


class SalesDataset(Dataset):
    """PyTorch dataset for sales time series data"""
    
    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class LSTMSalesPredictor(nn.Module):
    """LSTM model for sales prediction"""
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        output_size: int = 7  # Predict 7 days ahead
    ):
        super().__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True
        )
        
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size,
            num_heads=4,
            dropout=dropout
        )
        
        self.fc_layers = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, output_size)
        )
    
    def forward(self, x):
        # LSTM forward pass
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Apply attention
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        # Use last hidden state
        last_hidden = attn_out[:, -1, :]
        
        # Final prediction
        output = self.fc_layers(last_hidden)
        
        return output


class SalesPredictor:
    """Main sales prediction system"""
    
    def __init__(self, config: Dict[str, Any], session: AsyncSession):
        self.config = config
        self.session = session
        self.cache = RedisCache(config['redis'])
        self.model_config = config['ml_models']['sales_prediction']
        
        self.models = {}
        self.scalers = {}
        self.feature_columns = self.model_config['features']
        self.sequence_length = self.model_config['sequence_length']
        
        # Device configuration
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
    
    async def prepare_training_data(
        self,
        marketplace: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data from database"""
        
        if not end_date:
            end_date = datetime.utcnow().date()
        if not start_date:
            start_date = end_date - timedelta(days=365)  # 1 year of data
        
        # Query performance data
        stmt = select(ProductPerformance).where(
            and_(
                ProductPerformance.marketplace == marketplace,
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        ).order_by(ProductPerformance.product_id, ProductPerformance.date)
        
        result = await self.session.execute(stmt)
        performances = result.scalars().all()
        
        # Group by product
        product_data = {}
        for perf in performances:
            if perf.product_id not in product_data:
                product_data[perf.product_id] = []
            
            # Extract features
            features = {
                'date': perf.date,
                'views': perf.views or 0,
                'clicks': perf.clicks or 0,
                'conversions': perf.conversions or 0,
                'sales_volume': perf.sales_volume or 0,
                'revenue': float(perf.revenue or 0),
                'ranking': perf.category_ranking or 999,
                'wish_count': perf.wish_count or 0
            }
            
            product_data[perf.product_id].append(features)
        
        # Create sequences
        sequences = []
        targets = []
        
        for product_id, data in product_data.items():
            if len(data) < self.sequence_length + 7:  # Need enough data for sequence + target
                continue
            
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(data)
            df = df.sort_values('date')
            
            # Create sequences
            for i in range(len(df) - self.sequence_length - 7 + 1):
                # Input sequence
                seq = df.iloc[i:i + self.sequence_length][self.feature_columns].values
                
                # Target (next 7 days sales)
                target = df.iloc[i + self.sequence_length:i + self.sequence_length + 7]['sales_volume'].values
                
                sequences.append(seq)
                targets.append(target)
        
        return np.array(sequences), np.array(targets)
    
    async def train_model(
        self,
        marketplace: str,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001
    ) -> Dict[str, Any]:
        """Train LSTM model for sales prediction"""
        logger.info(f"Training sales prediction model for {marketplace}")
        
        # Prepare data
        X, y = await self.prepare_training_data(marketplace)
        
        if len(X) < 100:
            return {
                'error': 'Insufficient data for training',
                'samples': len(X)
            }
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train.reshape(-1, X_train.shape[-1]))
        X_train_scaled = X_train_scaled.reshape(X_train.shape)
        
        X_val_scaled = scaler.transform(X_val.reshape(-1, X_val.shape[-1]))
        X_val_scaled = X_val_scaled.reshape(X_val.shape)
        
        # Scale targets
        target_scaler = MinMaxScaler()
        y_train_scaled = target_scaler.fit_transform(y_train)
        y_val_scaled = target_scaler.transform(y_val)
        
        # Create datasets
        train_dataset = SalesDataset(X_train_scaled, y_train_scaled)
        val_dataset = SalesDataset(X_val_scaled, y_val_scaled)
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False
        )
        
        # Initialize model
        model = LSTMSalesPredictor(
            input_size=len(self.feature_columns),
            hidden_size=128,
            num_layers=2,
            dropout=0.2,
            output_size=7
        ).to(self.device)
        
        # Loss and optimizer
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', patience=5, factor=0.5
        )
        
        # Training loop
        train_losses = []
        val_losses = []
        best_val_loss = float('inf')
        
        for epoch in range(epochs):
            # Training
            model.train()
            train_loss = 0
            
            for sequences, targets in train_loader:
                sequences = sequences.to(self.device)
                targets = targets.to(self.device)
                
                optimizer.zero_grad()
                outputs = model(sequences)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            # Validation
            model.eval()
            val_loss = 0
            
            with torch.no_grad():
                for sequences, targets in val_loader:
                    sequences = sequences.to(self.device)
                    targets = targets.to(self.device)
                    
                    outputs = model(sequences)
                    loss = criterion(outputs, targets)
                    val_loss += loss.item()
            
            avg_train_loss = train_loss / len(train_loader)
            avg_val_loss = val_loss / len(val_loader)
            
            train_losses.append(avg_train_loss)
            val_losses.append(avg_val_loss)
            
            # Learning rate scheduling
            scheduler.step(avg_val_loss)
            
            # Save best model
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                torch.save(model.state_dict(), f'models/{marketplace}_sales_model.pth')
                joblib.dump(scaler, f'models/{marketplace}_feature_scaler.pkl')
                joblib.dump(target_scaler, f'models/{marketplace}_target_scaler.pkl')
            
            if epoch % 10 == 0:
                logger.info(
                    f"Epoch {epoch}/{epochs} - "
                    f"Train Loss: {avg_train_loss:.4f}, "
                    f"Val Loss: {avg_val_loss:.4f}"
                )
        
        # Store model in memory
        self.models[marketplace] = model
        self.scalers[marketplace] = {
            'feature': scaler,
            'target': target_scaler
        }
        
        return {
            'marketplace': marketplace,
            'epochs_trained': epochs,
            'final_train_loss': train_losses[-1],
            'final_val_loss': val_losses[-1],
            'best_val_loss': best_val_loss,
            'model_parameters': sum(p.numel() for p in model.parameters())
        }
    
    async def predict_sales(
        self,
        product_id: int,
        marketplace: str,
        prediction_days: int = 7
    ) -> Dict[str, Any]:
        """Predict future sales for a product"""
        
        # Check cache first
        cache_key = CacheKey.prediction(
            str(product_id),
            'sales',
            datetime.utcnow().date().isoformat()
        )
        cached_prediction = await self.cache.get(cache_key)
        if cached_prediction:
            return cached_prediction
        
        # Load model if not in memory
        if marketplace not in self.models:
            await self._load_model(marketplace)
        
        model = self.models.get(marketplace)
        if not model:
            return {'error': f'No model available for {marketplace}'}
        
        # Get recent performance data
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=self.sequence_length + 30)
        
        stmt = select(ProductPerformance).where(
            and_(
                ProductPerformance.product_id == product_id,
                ProductPerformance.marketplace == marketplace,
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        ).order_by(ProductPerformance.date)
        
        result = await self.session.execute(stmt)
        performances = result.scalars().all()
        
        if len(performances) < self.sequence_length:
            return {
                'error': 'Insufficient historical data',
                'required': self.sequence_length,
                'available': len(performances)
            }
        
        # Prepare input data
        data = []
        for perf in performances[-self.sequence_length:]:
            features = [
                perf.views or 0,
                perf.clicks or 0,
                perf.conversions or 0,
                float(perf.revenue or 0) / 1000,  # Scale revenue
                perf.category_ranking or 999,
                0,  # review_score placeholder
                0   # competitor_price placeholder
            ]
            data.append(features)
        
        # Scale and predict
        X = np.array(data).reshape(1, self.sequence_length, -1)
        scaler = self.scalers[marketplace]['feature']
        target_scaler = self.scalers[marketplace]['target']
        
        X_scaled = scaler.transform(X.reshape(-1, X.shape[-1]))
        X_scaled = X_scaled.reshape(X.shape)
        
        # Make prediction
        model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_scaled).to(self.device)
            prediction_scaled = model(X_tensor).cpu().numpy()
        
        # Inverse transform
        predictions = target_scaler.inverse_transform(prediction_scaled)[0]
        
        # Calculate confidence based on recent performance variance
        recent_sales = [p.sales_volume or 0 for p in performances[-30:]]
        variance = np.var(recent_sales) if recent_sales else 1
        confidence = max(0.5, min(0.95, 1 - (variance / (np.mean(recent_sales) + 1))))
        
        # Prepare prediction data
        prediction_dates = [
            (end_date + timedelta(days=i+1)).isoformat()
            for i in range(prediction_days)
        ]
        
        result = {
            'product_id': product_id,
            'marketplace': marketplace,
            'prediction_date': end_date.isoformat(),
            'predictions': {
                date: max(0, int(pred))  # Ensure non-negative
                for date, pred in zip(prediction_dates, predictions[:prediction_days])
            },
            'confidence_score': float(confidence),
            'model_version': '1.0',
            'features_used': self.feature_columns
        }
        
        # Save to database
        await self._save_prediction(product_id, marketplace, result)
        
        # Cache result
        await self.cache.set(cache_key, result, expire=3600)  # 1 hour cache
        
        return result
    
    async def _load_model(self, marketplace: str):
        """Load saved model from disk"""
        try:
            model = LSTMSalesPredictor(
                input_size=len(self.feature_columns),
                hidden_size=128,
                num_layers=2,
                dropout=0.2,
                output_size=7
            )
            
            model.load_state_dict(
                torch.load(f'models/{marketplace}_sales_model.pth', map_location=self.device)
            )
            model.to(self.device)
            model.eval()
            
            self.models[marketplace] = model
            
            # Load scalers
            self.scalers[marketplace] = {
                'feature': joblib.load(f'models/{marketplace}_feature_scaler.pkl'),
                'target': joblib.load(f'models/{marketplace}_target_scaler.pkl')
            }
            
            logger.info(f"Loaded sales prediction model for {marketplace}")
            
        except Exception as e:
            logger.error(f"Failed to load model for {marketplace}: {str(e)}")
    
    async def _save_prediction(
        self,
        product_id: int,
        marketplace: str,
        prediction_data: Dict[str, Any]
    ):
        """Save prediction to database"""
        prediction = AIPrediction(
            product_id=product_id,
            prediction_type='sales',
            model_name='lstm_sales_predictor',
            model_version=prediction_data['model_version'],
            predictions={
                'marketplace': marketplace,
                'daily_predictions': prediction_data['predictions']
            },
            confidence_score=prediction_data['confidence_score'],
            prediction_date=datetime.fromisoformat(prediction_data['prediction_date']).date(),
            prediction_horizon_days=len(prediction_data['predictions']),
            predicted_at=datetime.utcnow()
        )
        
        self.session.add(prediction)
        await self.session.commit()
    
    async def evaluate_predictions(
        self,
        marketplace: str,
        evaluation_days: int = 30
    ) -> Dict[str, Any]:
        """Evaluate prediction accuracy"""
        
        # Get predictions made at least 7 days ago
        cutoff_date = datetime.utcnow().date() - timedelta(days=7)
        
        stmt = select(AIPrediction).where(
            and_(
                AIPrediction.prediction_type == 'sales',
                AIPrediction.prediction_date <= cutoff_date - timedelta(days=evaluation_days),
                AIPrediction.predictions['marketplace'].astext == marketplace
            )
        )
        
        result = await self.session.execute(stmt)
        predictions = result.scalars().all()
        
        if not predictions:
            return {'error': 'No predictions to evaluate'}
        
        # Calculate metrics
        mae_values = []
        rmse_values = []
        mape_values = []
        
        for prediction in predictions:
            # Get actual values
            daily_predictions = prediction.predictions['daily_predictions']
            
            for date_str, predicted_value in daily_predictions.items():
                date = datetime.fromisoformat(date_str).date()
                
                # Get actual performance
                stmt = select(ProductPerformance).where(
                    and_(
                        ProductPerformance.product_id == prediction.product_id,
                        ProductPerformance.marketplace == marketplace,
                        ProductPerformance.date == date
                    )
                )
                
                result = await self.session.execute(stmt)
                actual_perf = result.scalar_one_or_none()
                
                if actual_perf and actual_perf.sales_volume is not None:
                    actual = actual_perf.sales_volume
                    predicted = predicted_value
                    
                    # Calculate errors
                    mae_values.append(abs(actual - predicted))
                    rmse_values.append((actual - predicted) ** 2)
                    if actual > 0:
                        mape_values.append(abs(actual - predicted) / actual)
        
        if not mae_values:
            return {'error': 'No actual data available for evaluation'}
        
        # Calculate final metrics
        mae = np.mean(mae_values)
        rmse = np.sqrt(np.mean(rmse_values))
        mape = np.mean(mape_values) * 100 if mape_values else None
        
        evaluation_result = {
            'marketplace': marketplace,
            'evaluation_period': f'{evaluation_days} days',
            'predictions_evaluated': len(predictions),
            'data_points': len(mae_values),
            'metrics': {
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape) if mape else None,
                'accuracy': float(100 - mape) if mape else None
            },
            'evaluated_at': datetime.utcnow().isoformat()
        }
        
        # Update predictions with evaluation metrics
        for prediction in predictions:
            if not prediction.evaluation_metrics:
                prediction.evaluation_metrics = evaluation_result['metrics']
                prediction.evaluated_at = datetime.utcnow()
        
        await self.session.commit()
        
        return evaluation_result