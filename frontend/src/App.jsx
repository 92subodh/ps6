import { useState } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { api } from './api/client';
import Navbar from './components/Navbar';
import AttackTheater from './pages/AttackTheater';
import CommandCenter from './pages/CommandCenter';
import MitigationEngine from './pages/MitigationEngine';
import MirrorPage from './pages/MirrorPage';
import VulnerabilityHeatmap from './pages/VulnerabilityHeatmap';

function App() {
  const navigate = useNavigate();
  const [demoMode, setDemoMode] = useState(false);
  const [whatIfQuery, setWhatIfQuery] = useState('');
  const [whatIfError, setWhatIfError] = useState('');
  const [isSubmittingWhatIf, setIsSubmittingWhatIf] = useState(false);

  const handleSubmitWhatIf = async () => {
    const query = whatIfQuery.trim();
    if (!query) {
      return;
    }

    setIsSubmittingWhatIf(true);
    setWhatIfError('');

    try {
      const response = await api.post('/what-if', {
        natural_language_query: query,
      });
      const attackId = response?.data?.attack_generated?.attack_id;
      const targetUrl =
        typeof attackId === 'number'
          ? '/attack-theater?attackId=' + String(attackId)
          : '/attack-theater';
      navigate(targetUrl);
      setWhatIfQuery('');
    } catch (error) {
      setWhatIfError('What-If request failed. Check backend status and try again.');
    } finally {
      setIsSubmittingWhatIf(false);
    }
  };

  return (
    <div className="min-h-screen pb-8">
      <Navbar
        demoMode={demoMode}
        setDemoMode={setDemoMode}
        whatIfQuery={whatIfQuery}
        setWhatIfQuery={setWhatIfQuery}
        onSubmitWhatIf={handleSubmitWhatIf}
        whatIfError={whatIfError}
        isSubmittingWhatIf={isSubmittingWhatIf}
      />

      <main className="mx-auto mt-6 w-[95%] max-w-[1500px]">
        <Routes>
          <Route path="/" element={<Navigate to="/command-center" replace />} />
          <Route path="/command-center" element={<CommandCenter demoMode={demoMode} />} />
          <Route path="/attack-theater" element={<AttackTheater demoMode={demoMode} />} />
          <Route
            path="/vulnerability-heatmap"
            element={<VulnerabilityHeatmap demoMode={demoMode} />}
          />
          <Route path="/mitigation-engine" element={<MitigationEngine demoMode={demoMode} />} />
          <Route path="/mirror" element={<MirrorPage demoMode={demoMode} />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
