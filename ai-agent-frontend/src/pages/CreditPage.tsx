import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { useLanguageStore } from '../store/languageStore';
import { apiService } from '../services/api/api';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { 
  CreditCard, 
  Wallet, 
  Plus, 
  Gift, 
  History, 
  DollarSign,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  Copy
} from 'lucide-react';

interface CreditTransaction {
  id: number;
  type: 'purchase' | 'credit_code' | 'topup' | 'refund';
  amount: number;
  description: string;
  status: 'pending' | 'completed' | 'failed' | 'refunded';
  created_at: string;
}

export const CreditPage: React.FC = () => {
  const { user, updateUser } = useAuthStore();
  const { language } = useLanguageStore();
  const [balance, setBalance] = useState(0);
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [promoCode, setPromoCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadBalance();
    loadTransactions();
  }, []);

  const loadBalance = async () => {
    try {
      const response = await apiService.getUserBalance();
      setBalance(response.balance);
    } catch (error) {
      console.error('Failed to load balance:', error);
    }
  };

  const loadTransactions = async () => {
    try {
      const response = await apiService.getCreditTransactions({ limit: 20 });
      setTransactions(response.items);
    } catch (error) {
      console.error('Failed to load transactions:', error);
    }
  };

  const handleRedeemPromoCode = async () => {
    if (!promoCode.trim()) return;
    
    setIsLoading(true);
    setMessage(null);
    
    try {
      const response = await apiService.redeemCreditCode(promoCode.trim());
      setBalance(response.balance);
      setPromoCode('');
      setMessage({ 
        type: 'success', 
        text: response.message || (language === 'ar' ? 'تم تطبيق الكود بنجاح' : 'Code applied successfully')
      });
      
      // Update user balance in store
      updateUser({ balance: response.balance });
      
      // Reload transactions
      loadTransactions();
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.message || (language === 'ar' ? 'فشل في تطبيق الكود' : 'Failed to apply code')
      });
    } finally {
      setIsLoading(false);
      setTimeout(() => setMessage(null), 5000);
    }
  };

  const handlePurchaseCredits = async (amount: number) => {
    setIsLoading(true);
    try {
      const response = await apiService.initializePayment({
        amount,
        currency: 'USD',
        payment_method: 'stripe'
      });
      
      // Redirect to payment page or open payment modal
      window.open(response.checkout_url, '_blank');
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.message || (language === 'ar' ? 'فشل في معالجة الدفع' : 'Payment processing failed')
      });
    } finally {
      setIsLoading(false);
      setTimeout(() => setMessage(null), 5000);
    }
  };

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'purchase':
      case 'topup':
        return <DollarSign className="h-4 w-4 text-green-600" />;
      case 'credit_code':
        return <Gift className="h-4 w-4 text-blue-600" />;
      case 'refund':
        return <ArrowRight className="h-4 w-4 text-orange-600" />;
      default:
        return <DollarSign className="h-4 w-4 text-gray-600" />;
    }
  };

  const getTransactionStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'pending':
        return <AlertCircle className="h-4 w-4 text-yellow-600" />;
      case 'failed':
      case 'refunded':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-600" />;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(language === 'ar' ? 'ar-SA' : 'en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const creditPackages = [
    { amount: 10, price: 10, bonus: 0, popular: false },
    { amount: 25, price: 25, bonus: 5, popular: false },
    { amount: 50, price: 50, bonus: 15, popular: true },
    { amount: 100, price: 100, bonus: 40, popular: false },
    { amount: 250, price: 250, bonus: 125, popular: false },
  ];

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">
          {language === 'ar' ? 'إدارة الرصيد' : 'Credit Management'}
        </h1>
        <p className="text-muted-foreground">
          {language === 'ar' ? 'إدارة رصيدك ومشترياتك' : 'Manage your balance and purchases'}
        </p>
      </div>

      {message && (
        <div className={`p-4 rounded-md mb-6 ${
          message.type === 'success' 
            ? 'bg-green-50 text-green-700 border border-green-200' 
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Balance Card */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 rtl:space-x-reverse">
                <Wallet className="h-5 w-5" />
                <span>{language === 'ar' ? 'الرصيد الحالي' : 'Current Balance'}</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center">
                <div className="text-3xl font-bold text-primary mb-2">
                  ${balance.toFixed(2)}
                </div>
                <p className="text-muted-foreground text-sm mb-4">
                  {language === 'ar' ? 'رصيد متاح للاستخدام' : 'Available balance'}
                </p>
                
                {/* Quick Actions */}
                <div className="space-y-2">
                  <Button
                    className="w-full"
                    onClick={() => handlePurchaseCredits(25)}
                    disabled={isLoading}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    {language === 'ar' ? 'إضافة رصيد' : 'Add Credits'}
                  </Button>
                  
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => {/* TODO: Open usage stats */}}
                  >
                    <History className="h-4 w-4 mr-2" />
                    {language === 'ar' ? 'الإحصائيات' : 'Statistics'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Promo Code Card */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 rtl:space-x-reverse">
                <Gift className="h-5 w-5" />
                <span>{language === 'ar' ? 'كود خصم' : 'Promo Code'}</span>
              </CardTitle>
              <CardDescription>
                {language === 'ar' ? 'أدخل كود الخصم للحصول على رصيد مجاني' : 'Enter promo code for free credits'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex space-x-2 rtl:space-x-reverse">
                <Input
                  value={promoCode}
                  onChange={(e) => setPromoCode(e.target.value)}
                  placeholder={language === 'ar' ? 'أدخل كود الخصم' : 'Enter promo code'}
                  disabled={isLoading}
                />
                <Button
                  onClick={handleRedeemPromoCode}
                  disabled={!promoCode.trim() || isLoading}
                  loading={isLoading}
                >
                  {language === 'ar' ? 'تطبيق' : 'Apply'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Purchase Packages */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 rtl:space-x-reverse">
                <CreditCard className="h-5 w-5" />
                <span>{language === 'ar' ? 'شراء أرصدة' : 'Purchase Credits'}</span>
              </CardTitle>
              <CardDescription>
                {language === 'ar' ? 'اختر باقة الأرصدة المناسبة لك' : 'Choose the credit package that suits you'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {creditPackages.map((pkg) => (
                  <div
                    key={pkg.amount}
                    className={`relative border rounded-lg p-4 cursor-pointer transition-all hover:shadow-md ${
                      pkg.popular 
                        ? 'border-primary bg-primary/5' 
                        : 'border-border hover:border-primary/50'
                    }`}
                    onClick={() => handlePurchaseCredits(pkg.amount)}
                  >
                    {pkg.popular && (
                      <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
                        <span className="bg-primary text-primary-foreground text-xs px-2 py-1 rounded-full">
                          {language === 'ar' ? 'الأكثر شعبية' : 'Popular'}
                        </span>
                      </div>
                    )}
                    
                    <div className="text-center">
                      <div className="text-2xl font-bold mb-1">
                        ${pkg.amount}
                      </div>
                      <div className="text-sm text-muted-foreground mb-2">
                        ${pkg.price}
                      </div>
                      
                      {pkg.bonus > 0 && (
                        <div className="text-xs text-green-600 font-medium mb-2">
                          +${pkg.bonus} {language === 'ar' ? 'مكافأة' : 'bonus'}
                        </div>
                      )}
                      
                      <Button
                        variant={pkg.popular ? 'default' : 'outline'}
                        size="sm"
                        className="w-full"
                        disabled={isLoading}
                      >
                        {language === 'ar' ? 'شراء' : 'Buy'}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Transaction History */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 rtl:space-x-reverse">
            <History className="h-5 w-5" />
            <span>{language === 'ar' ? 'سجل المعاملات' : 'Transaction History'}</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {transactions.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">
                {language === 'ar' ? 'لا توجد معاملات بعد' : 'No transactions yet'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {transactions.map((transaction) => (
                <div
                  key={transaction.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center space-x-3 rtl:space-x-reverse">
                    {getTransactionIcon(transaction.type)}
                    <div>
                      <div className="font-medium">{transaction.description}</div>
                      <div className="text-sm text-muted-foreground">
                        {formatDate(transaction.created_at)}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 rtl:space-x-reverse">
                    <div className={`font-medium ${
                      transaction.type === 'refund' 
                        ? 'text-red-600' 
                        : transaction.type === 'credit_code'
                        ? 'text-green-600'
                        : 'text-gray-900'
                    }`}>
                      {transaction.type === 'refund' ? '-' : '+'}${Math.abs(transaction.amount).toFixed(2)}
                    </div>
                    {getTransactionStatusIcon(transaction.status)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};